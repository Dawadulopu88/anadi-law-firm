"""Shared role checks. Roles do not imply access to every object."""
from rest_framework.permissions import BasePermission, SAFE_METHODS

FIRM_ROLES = frozenset({'admin', 'lawyer', 'staff'})


def has_role(user, *roles):
    return bool(
        user and user.is_authenticated and user.is_active
        and getattr(user, 'role', None) in roles
    )


def is_firm_member(user):
    return has_role(user, *FIRM_ROLES)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'admin')


class IsLawyer(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'lawyer')


class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'staff')


class IsClient(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'client')


class IsFirmMember(BasePermission):
    def has_permission(self, request, view):
        return is_firm_member(request.user)


class IsFirmMemberOrClientReadOnly(BasePermission):
    """Client-record permission; combine with an ownership-filtered queryset."""

    def has_permission(self, request, view):
        return is_firm_member(request.user) or (
            request.method in SAFE_METHODS and has_role(request.user, 'client')
        )

    def has_object_permission(self, request, view, obj):
        return is_firm_member(request.user) or (
            request.method in SAFE_METHODS and has_role(request.user, 'client')
            and obj.user_id == request.user.pk
        )
