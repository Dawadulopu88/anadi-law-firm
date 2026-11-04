from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.permissions import has_role, is_firm_member


def visible_cases(user):
    from .models import Case
    queryset = Case.objects.select_related('client', 'practice_area')
    if has_role(user, 'admin', 'staff'):
        return queryset
    if has_role(user, 'lawyer'):
        return queryset.filter(assignments__user=user)
    if has_role(user, 'client'):
        return queryset.filter(client__user=user)
    return queryset.none()


class CanAccessCases(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return is_firm_member(request.user) or has_role(request.user, 'client')
        if view.action == 'create':
            return has_role(request.user, 'admin', 'staff')
        return is_firm_member(request.user)


class CanAccessNotes(BasePermission):
    def has_permission(self, request, view):
        return is_firm_member(request.user) or (
            request.method in SAFE_METHODS and has_role(request.user, 'client')
        )


class CanManageAssignments(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'admin', 'staff') or (
            request.method in SAFE_METHODS and has_role(request.user, 'lawyer')
        )
