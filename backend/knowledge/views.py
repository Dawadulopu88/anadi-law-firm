from django.db.models import Q
from rest_framework import generics, viewsets, serializers
from rest_framework.permissions import AllowAny
from .models import Jurisdiction, RightsTopic, KnowledgeArticle, FAQ
from .serializers import JurisdictionSerializer, TopicSerializer, ArticleSerializer, FAQSerializer
from .services import public_content


def content_filters(queryset, params):
    for parameter, field in (('jurisdiction', 'jurisdiction__code'), ('topic', 'topic__slug'), ('language', 'language')):
        if params.get(parameter):
            queryset = queryset.filter(**{field: params[parameter]})
    return queryset


class PublicReadOnly(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]


class JurisdictionViewSet(PublicReadOnly):
    queryset = Jurisdiction.objects.all()
    serializer_class = JurisdictionSerializer
    lookup_field = 'code'


class TopicViewSet(PublicReadOnly):
    queryset = RightsTopic.objects.filter(is_active=True)
    serializer_class = TopicSerializer
    lookup_field = 'slug'


class ArticleViewSet(PublicReadOnly):
    serializer_class = ArticleSerializer
    lookup_field = 'slug'
    def get_queryset(self):
        return content_filters(public_content(KnowledgeArticle), self.request.query_params)


class FAQViewSet(PublicReadOnly):
    serializer_class = FAQSerializer
    def get_queryset(self):
        return content_filters(public_content(FAQ), self.request.query_params)


class SearchView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query or len(query) > 200:
            raise serializers.ValidationError({'q': 'Provide between 1 and 200 characters.'})
        articles = content_filters(public_content(KnowledgeArticle), request.query_params).filter(Q(title__icontains=query) | Q(summary__icontains=query) | Q(body__icontains=query))
        faqs = content_filters(public_content(FAQ), request.query_params).filter(Q(question__icontains=query) | Q(answer__icontains=query))
        # UNION keeps pagination in SQL and does not materialize entire article bodies.
        from django.db.models import Value, CharField
        hits = articles.annotate(kind=Value('article', output_field=CharField())).values_list('kind', 'pk').order_by().union(
            faqs.annotate(kind=Value('faq', output_field=CharField())).values_list('kind', 'pk').order_by()
        ).order_by('kind', 'pk')
        page = self.paginate_queryset(hits)
        article_map = {o.pk: o for o in articles.filter(pk__in=[pk for kind, pk in page if kind == 'article'])}
        faq_map = {o.pk: o for o in faqs.filter(pk__in=[pk for kind, pk in page if kind == 'faq'])}
        data = []
        for kind, pk in page:
            obj = (article_map if kind == 'article' else faq_map).get(pk)
            if obj is not None:
                data.append({'type': kind, **(ArticleSerializer(obj).data if kind == 'article' else FAQSerializer(obj).data)})
        return self.get_paginated_response(data)
