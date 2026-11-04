from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .permissions import has_role


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Account administration can change roles and privileges. Model permissions
    # alone must not grant this power to a client/lawyer/staff application role.
    def has_module_permission(self, request):
        return has_role(request.user, 'admin') and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return has_role(request.user, 'admin') and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return has_role(request.user, 'admin') and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return has_role(request.user, 'admin') and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return has_role(request.user, 'admin') and super().has_delete_permission(request, obj)

    fieldsets = UserAdmin.fieldsets + (
        ('Law firm details', {'fields': ('role', 'phone')}),
    )
    list_display = ('username', 'email', 'role', 'is_active')
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Law firm details', {'fields': ('role', 'phone')}),
    )
    list_filter = ('role', 'is_active')
