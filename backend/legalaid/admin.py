from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from intake.admin import FirmMemberAdmin
from .models import LegalAidApplication
from .services import convert_application


@admin.register(LegalAidApplication)
class ApplicationAdmin(FirmMemberAdmin):
    list_display = ('applicant_name', 'practice_area', 'status', 'created_at')
    list_filter = ('status', 'practice_area')
    search_fields = ('applicant_name', 'tracking_code')
    readonly_fields = ('tracking_code', 'applicant_name', 'phone', 'email', 'practice_area', 'description', 'income_range', 'eligibility_answers', 'client', 'case', 'reviewed_by', 'created_at', 'updated_at')
    actions = ['convert_selected']
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, 'status') if obj and obj.status == 'matched' else self.readonly_fields
    def save_model(self, request, obj, form, change):
        obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)
    @admin.action(description='Convert to client and case', permissions=['change'])
    def convert_selected(self, request, queryset):
        for obj in queryset:
            try:
                convert_application(obj.pk, request.user)
            except ValidationError as error:
                self.message_user(request, ' '.join(error.messages), messages.ERROR)
