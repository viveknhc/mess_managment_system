"""Gate a view on a business feature: ``permission_classes = [IsAuthenticated, requires_feature(REPORTS)]``."""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.customization.registry import FEATURES
from apps.customization.services import FeatureService
from common.constants import Role


class FeatureDisabled(PermissionDenied):
    error_code = "FEATURE_DISABLED"


def requires_feature(key):
    if key not in FEATURES:
        raise ValueError(f"Unknown feature {key!r}.")

    class RequiresFeature(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            if getattr(user, "role", None) == Role.SUPER_ADMIN:
                return True
            if not FeatureService.has(getattr(user, "business_id", None), key):
                raise FeatureDisabled(f"{FEATURES[key].label} is not enabled for this business.")
            return True

    RequiresFeature.__name__ = f"Requires_{key}"
    return RequiresFeature
