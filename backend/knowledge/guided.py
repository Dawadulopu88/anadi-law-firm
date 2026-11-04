from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from firm.serializers import LocalizedSerializer, PracticeAreaSerializer
from .models import GuidedFlow, GuidedQuestion, GuidedOption, HelpContact, KnowledgeArticle
from .serializers import disclaimer, ArticleSerializer
from .services import public_content


def validate_flow(flow):
    if not flow.pk or not flow.start_question_id:
        raise ValidationError('Select a start question before activating the flow.')
    questions = list(flow.questions.prefetch_related('options'))
    if len(questions) > 100:
        raise ValidationError('A flow can have at most 100 questions.')
    nodes = {question.pk: question for question in questions}
    active_articles = set(public_content(KnowledgeArticle).values_list('pk', flat=True))
    from firm.models import PracticeArea
    active_areas = set(PracticeArea.objects.filter(is_active=True).values_list('pk', flat=True))
    visited, stack = set(), set()
    def visit(pk):
        if pk in stack or pk not in nodes:
            raise ValidationError('Flow contains a cycle or a question outside the flow.')
        if pk in visited:
            return
        stack.add(pk)
        options = list(nodes[pk].options.all())
        if not options:
            raise ValidationError('Every reachable question needs at least one option.')
        for option in options:
            if option.next_question_id:
                visit(option.next_question_id)
            elif not (option.escalate_to_consultation or option.outcome_article_id in active_articles or option.outcome_practice_area_id in active_areas):
                raise ValidationError('A terminal option needs a currently available outcome.')
        stack.remove(pk)
        visited.add(pk)
    visit(flow.start_question_id)
    return visited


def public_flow(pk):
    flow = get_object_or_404(GuidedFlow, pk=pk, is_active=True)
    try:
        nodes = validate_flow(flow)
    except ValidationError:
        raise Http404('Flow is unavailable.')
    return flow, nodes


class FlowSerializer(LocalizedSerializer):
    localized_fields = ('name',)
    class Meta:
        model = GuidedFlow
        fields = ('id', 'name', 'purpose', 'start_question', 'is_sample')


class OptionSerializer(LocalizedSerializer):
    localized_fields = ('label',)
    class Meta:
        model = GuidedOption
        fields = ('id', 'label', 'next_question')


class QuestionSerializer(LocalizedSerializer):
    localized_fields = ('text',)
    options = OptionSerializer(many=True, read_only=True)
    class Meta:
        model = GuidedQuestion
        fields = ('id', 'flow', 'text', 'order', 'options')


class ContactSerializer(LocalizedSerializer):
    localized_fields = ('label', 'hours')
    class Meta:
        model = HelpContact
        fields = ('id', 'label', 'phone', 'hours', 'is_emergency', 'display_order')


class ContactList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ContactSerializer
    queryset = HelpContact.objects.filter(verified_by__isnull=False, verified_at__isnull=False).exclude(verification_reference='')


class FlowViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = FlowSerializer
    def get_queryset(self):
        ids = []
        for flow in GuidedFlow.objects.filter(is_active=True):
            try:
                validate_flow(flow)
                ids.append(flow.pk)
            except ValidationError:
                pass
        return GuidedFlow.objects.filter(pk__in=ids)

    @action(detail=True, methods=['get'])
    def start(self, request, pk=None):
        flow, _ = public_flow(pk)
        return Response({'flow': FlowSerializer(flow).data, 'question': QuestionSerializer(flow.start_question).data, 'disclaimer': disclaimer(), 'indicative_only': True})


class QuestionDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = QuestionSerializer
    def get_object(self):
        question = get_object_or_404(GuidedQuestion, pk=self.kwargs['pk'])
        _, nodes = public_flow(question.flow_id)
        if question.pk not in nodes:
            raise Http404
        return question


class ResultView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    def get(self, request, pk):
        option = get_object_or_404(GuidedOption.objects.select_related('question', 'outcome_practice_area'), pk=pk, next_question__isnull=True)
        flow, nodes = public_flow(option.question.flow_id)
        if option.question_id not in nodes:
            raise Http404
        articles = public_content(KnowledgeArticle).filter(pk=option.outcome_article_id)
        area = option.outcome_practice_area
        return Response({'practice_area': PracticeAreaSerializer(area).data if area and area.is_active else None,
                         'articles': ArticleSerializer(articles, many=True).data,
                         'consultation_url': '/api/consultations/', 'escalate_to_consultation': option.escalate_to_consultation,
                         'disclaimer': disclaimer(), 'indicative_only': True, 'is_sample': flow.is_sample,
                         'message': 'This result is indicative only. Contact the firm for an individual assessment.'})
