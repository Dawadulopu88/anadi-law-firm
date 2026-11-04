from django import forms
from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html
from cases.admin import CaseScopedAdmin
from .models import Document
from .views import download_document, visible_documents


@admin.register(Document)
class DocumentAdmin(CaseScopedAdmin):
    list_display = ('title', 'case', 'version', 'is_client_visible', 'uploaded_at')
    list_filter = ('is_client_visible', 'document_type')
    search_fields = ('title', 'case__case_number')
    readonly_fields = ('uploaded_by', 'uploaded_at', 'updated_at', 'private_download')
    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, 'case', 'version') if obj else self.readonly_fields
    def get_exclude(self, request, obj=None):
        return ('file',) if obj else ()
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'file':
            kwargs['widget'] = forms.FileInput
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    def has_delete_permission(self, request, obj=None):
        return False
    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    @admin.display(description='Private download')
    def private_download(self, obj):
        if not obj.pk:
            return 'Save to enable authenticated download.'
        return format_html('<a href="{}">Download</a>', reverse('admin:document_download', args=[obj.pk]))
    def get_urls(self):
        return [path('<int:pk>/download/', self.admin_site.admin_view(self.download), name='document_download')] + super().get_urls()
    def download(self, request, pk):
        obj = get_object_or_404(visible_documents(request.user), pk=pk)
        if not self.has_view_permission(request, obj):
            raise PermissionDenied
        return download_document(obj)
