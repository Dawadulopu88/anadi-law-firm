from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect

from accounts.permissions import is_firm_member
from .models import Appointment, ConsultationRequest
from .services import convert_consultation


class FirmMemberAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return is_firm_member(request.user) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return is_firm_member(request.user) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return is_firm_member(request.user) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return is_firm_member(request.user) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return is_firm_member(request.user) and super().has_delete_permission(request, obj)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset if is_firm_member(request.user) else queryset.none()

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except ValidationError as error:
            # A concurrent booking/conversion may invalidate a form after validation.
            # The surrounding Admin transaction has already rolled back.
            if request.method != 'POST':
                raise
            self.message_user(request, 'Not saved: ' + ' '.join(error.messages), level=messages.ERROR)
            return HttpResponseRedirect(request.path)


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(FirmMemberAdmin):
    list_display = ('name', 'practice_area', 'status', 'preferred_date', 'handled_by', 'created_at')
    list_filter = ('status', 'preferred_language', 'practice_area')
    search_fields = ('name', 'phone', 'email')
    list_select_related = ('practice_area', 'handled_by')
    actions = ['convert_selected']
    readonly_fields = ('name', 'phone', 'email', 'practice_area', 'message', 'preferred_date', 'preferred_language', 'handled_by', 'client', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == ConsultationRequest.Status.CONVERTED:
            return (*self.readonly_fields, 'status')
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        obj.handled_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Convert selected requests to clients', permissions=['change'])
    def convert_selected(self, request, queryset):
        created = 0
        for request_id in queryset.values_list('pk', flat=True):
            try:
                _, was_created = convert_consultation(request_id, request.user)
                created += int(was_created)
            except ValidationError as error:
                self.message_user(request, f'Request {request_id}: ' + ' '.join(error.messages), level=messages.WARNING)
        self.message_user(request, f'{created} new client record(s) created.')


@admin.register(Appointment)
class AppointmentAdmin(FirmMemberAdmin):
    list_display = ('client', 'case', 'lawyer', 'start', 'end', 'appointment_type', 'status')
    list_filter = ('status', 'appointment_type', 'lawyer')
    search_fields = ('client__full_name', 'lawyer__first_name', 'lawyer__last_name')
    autocomplete_fields = ('client', 'case')
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    list_select_related = ('client', 'lawyer', 'case')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'case':
            from cases.permissions import visible_cases
            kwargs['queryset'] = visible_cases(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
