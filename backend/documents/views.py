from pathlib import Path
from django.http import FileResponse, Http404
from rest_framework import mixins, viewsets, serializers
from rest_framework.decorators import action
from accounts.permissions import has_role
from cases.permissions import CanAccessNotes, visible_cases
from cases.serializers import AccessibleCaseSerializer
from cases.views import filter_id
from .models import Document


def visible_documents(user):
    queryset = Document.objects.filter(case__in=visible_cases(user))
    return queryset.filter(is_client_visible=True) if has_role(user, 'client') else queryset


def download_document(document):
    try:
        stream = document.file.open('rb')
    except (OSError, ValueError):
        raise Http404('File unavailable.')
    response = FileResponse(stream, as_attachment=True, filename=f'document-{document.pk}-v{document.version}{Path(document.file.name).suffix}', content_type='application/octet-stream')
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


class DocumentSerializer(AccessibleCaseSerializer):
    file = serializers.FileField(write_only=True)
    download_url = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields['file'].required = False

    def get_download_url(self, obj):
        return f'/api/documents/{obj.pk}/download/'

    class Meta:
        model = Document
        fields = ('id', 'case', 'title', 'document_type', 'file', 'version', 'uploaded_by', 'is_client_visible', 'uploaded_at', 'updated_at', 'download_url')
        read_only_fields = ('id', 'uploaded_by', 'uploaded_at', 'updated_at')

    def validate(self, attrs):
        if self.instance and 'file' in attrs:
            raise serializers.ValidationError({'file': 'Upload a new document version instead.'})
        return attrs


class OwnDocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    def get_download_url(self, obj):
        return f'/api/documents/{obj.pk}/download/'
    class Meta:
        model = Document
        fields = ('id', 'case', 'title', 'document_type', 'version', 'uploaded_at', 'download_url')
        read_only_fields = fields


class DocumentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [CanAccessNotes]
    def get_queryset(self):
        return filter_id(visible_documents(self.request.user), self.request.query_params, 'case')
    def get_serializer_class(self):
        return OwnDocumentSerializer if has_role(self.request.user, 'client') else DocumentSerializer
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        return download_document(self.get_object())
