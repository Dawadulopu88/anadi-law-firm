from django.contrib import admin, messages
from django.db import IntegrityError
from django.http import HttpResponseRedirect

from accounts.permissions import has_role
from intake.admin import FirmMemberAdmin
from .models import Case, CaseAssignment, CaseNote, Hearing, Task
from .permissions import visible_cases


class CaseScopedAdmin(FirmMemberAdmin):
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        allowed = visible_cases(request.user)
        return queryset.filter(pk__in=allowed.values('pk')) if self.model is Case else queryset.filter(case__in=allowed)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self.allowed_object(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self.allowed_object(request, obj)

    def allowed_object(self, request, obj):
        return obj is None or visible_cases(request.user).filter(pk=obj.pk if self.model is Case else obj.case_id).exists()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'case':
            kwargs['queryset'] = visible_cases(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except IntegrityError:
            if request.method != 'POST':
                raise
            self.message_user(request, 'Not saved: a duplicate record was submitted. Reload and try again.', level=messages.ERROR)
            return HttpResponseRedirect(request.path)


@admin.register(Case)
class CaseAdmin(CaseScopedAdmin):
    list_display = ('case_number', 'title', 'client', 'practice_area', 'status', 'priority', 'filing_date')
    list_filter = ('status', 'priority', 'practice_area')
    search_fields = ('case_number', 'title')
    autocomplete_fields = ('client',)
    list_select_related = ('client', 'practice_area')
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return has_role(request.user, 'admin', 'staff') and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, 'client') if obj else self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CaseAssignment)
class CaseAssignmentAdmin(CaseScopedAdmin):
    list_display = ('case', 'user', 'role', 'assigned_by', 'assigned_at')
    list_filter = ('role', 'user__role')
    search_fields = ('case__case_number', 'case__title', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('case',)
    readonly_fields = ('assigned_by', 'assigned_at')
    list_select_related = ('case', 'user', 'assigned_by')

    def has_add_permission(self, request):
        return has_role(request.user, 'admin', 'staff') and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return has_role(request.user, 'admin', 'staff') and super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        obj.assigned_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CaseNote)
class CaseNoteAdmin(CaseScopedAdmin):
    list_display = ('case', 'is_internal', 'author', 'created_at')
    list_filter = ('is_internal',)
    search_fields = ('case__case_number', 'body')
    autocomplete_fields = ('case',)
    readonly_fields = ('author', 'created_at')
    list_select_related = ('case', 'author')

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(Hearing)
class HearingAdmin(CaseScopedAdmin):
    list_display = ('case', 'court_name', 'hearing_at', 'next_hearing_date')
    search_fields = ('case__case_number', 'court_name')
    autocomplete_fields = ('case',)
    readonly_fields = ('created_at', 'updated_at')

    def has_delete_permission(self, request, obj=None):
        return self.allowed_object(request, obj) and super().has_delete_permission(request, obj)


@admin.register(Task)
class TaskAdmin(FirmMemberAdmin):
    list_display = ('title', 'case', 'assigned_to', 'status', 'due_date')
    list_filter = ('status', 'priority')
    search_fields = ('title',)
    readonly_fields = ('created_by', 'created_at', 'updated_at')

    def get_queryset(self, request):
        from .work import visible_tasks
        return super().get_queryset(request).filter(pk__in=visible_tasks(request.user))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'case':
            kwargs['queryset'] = visible_cases(request.user)
        if db_field.name == 'assigned_to' and has_role(request.user, 'lawyer'):
            from django.contrib.auth import get_user_model
            kwargs['queryset'] = get_user_model().objects.filter(pk=request.user.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
