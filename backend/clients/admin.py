from django.contrib import admin

from accounts.permissions import is_firm_member
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'status', 'phone', 'email', 'assigned_lawyer', 'user', 'created_at')
    list_filter = ('status', 'assigned_lawyer')
    search_fields = ('full_name', 'phone', 'email', 'nid_or_reference')
    # User Admin is restricted to application admins. A normal filtered select
    # lets authorised firm staff link client accounts without account-admin access.
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    list_select_related = ('user', 'assigned_lawyer')
    fieldsets = (
        ('Client details', {'fields': ('full_name', 'phone', 'email', 'address', 'status', 'assigned_lawyer')}),
        ('Portal account', {'fields': ('user',)}),
        ('Internal information', {'fields': ('nid_or_reference', 'notes')}),
        ('Record history', {'fields': ('created_by', 'created_at', 'updated_at')}),
    )

    def has_module_permission(self, request):
        return is_firm_member(request.user) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return is_firm_member(request.user) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return is_firm_member(request.user) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return is_firm_member(request.user) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset if is_firm_member(request.user) else queryset.none()

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
