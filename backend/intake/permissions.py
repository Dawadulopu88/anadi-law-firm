from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.permissions import has_role, is_firm_member


class CanAccessAppointment(BasePermission):
    def has_permission(self, request, view):
        return is_firm_member(request.user) or (
            request.method in SAFE_METHODS and has_role(request.user, 'client')
        )

    def has_object_permission(self, request, view, obj):
        return is_firm_member(request.user) or (
            request.method in SAFE_METHODS and has_role(request.user, 'client')
            and obj.client.user_id == request.user.pk
        )
