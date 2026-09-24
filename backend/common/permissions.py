"""Permission classes (arch. §5, §10)."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from common.constants import Role


class IsSameBusiness(BasePermission):
    """Object-level tenant check.

    Viewsets query only the tenant's rows, so foreign objects 404 before this
    runs; this is the second line of defense on retrieve/update/delete.
    """

    message = "No such object."  # do not leak existence

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, "role", None) == Role.SUPER_ADMIN:
            return True
        business_id = getattr(obj, "business_id", None)
        return business_id is not None and business_id == request.user.business_id


class RoleBasedPermission(BasePermission):
    """Map allowed roles per view via `role_map = {action: [roles]}`.

    Unmapped actions default to owner/manager only. Read methods may allow a
    broader `read_roles` list.
    """

    message = "Your role cannot perform this action."

    def has_permission(self, request, view):
        role = getattr(request.user, "role", None)
        if role == Role.SUPER_ADMIN:
            return True

        role_map = getattr(view, "role_map", None)
        if not role_map:
            return role in (Role.OWNER, Role.MANAGER)

        action = getattr(view, "action", None)
        allowed = role_map.get(action)
        if request.method in SAFE_METHODS:
            read_roles = getattr(view, "read_roles", None)
            if read_roles and role in read_roles:
                return True
            if allowed is None:
                allowed = role_map.get("list", [])
        return role in (allowed or [])
