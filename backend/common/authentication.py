"""JWT authentication that also enforces business suspension.

Suspension is checked here, not per view, so every endpoint (viewsets, APIViews,
portal views) is covered. A suspended business keeps access to auth and billing
endpoints so the owner can still log in and see what to pay.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.constants import Role, Status

SUSPENDED_ALLOWED_PREFIXES = ("/api/v1/auth/", "/api/v1/billing/")


class BusinessSuspended(PermissionDenied):
    default_detail = "Your business account is suspended. Please contact support."
    error_code = "BUSINESS_SUSPENDED"


class TenantJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user = result[0]
        if getattr(user, "role", None) != Role.SUPER_ADMIN and not request.path.startswith(
            SUSPENDED_ALLOWED_PREFIXES
        ):
            business = getattr(user, "business", None)
            if business is not None and business.status == Status.SUSPENDED:
                raise BusinessSuspended()
        return result
