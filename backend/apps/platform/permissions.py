"""Platform-level permission classes."""

from rest_framework.permissions import BasePermission

from common.constants import Role


class IsSuperAdmin(BasePermission):
    """Only SUPER_ADMIN users can access platform management endpoints."""

    message = "Platform admin access required."

    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == Role.SUPER_ADMIN


class IsOwnerOrManager(BasePermission):
    """Business owners/managers — for billing endpoints."""

    message = "Business owner or manager access required."

    def has_permission(self, request, view):
        return getattr(request.user, "role", None) in (Role.OWNER, Role.MANAGER)
