"""JWT authentication that also enforces business access (suspension + unpaid onboarding).

Checked here, not per view, so every endpoint (viewsets, APIViews, portal views) is
covered. A locked business keeps access to auth and billing endpoints so the owner can
still log in and pay.

Two locks:
- business.status == SUSPENDED          → 403 BUSINESS_SUSPENDED
- SaaS billing still PENDING (first payment — setup fee + first month — never made)
                                         → 403 PAYMENT_REQUIRED
A business with no SaasSubscription row (bootstrap / own-software installs) is not locked.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.constants import Role, Status

LOCKED_ALLOWED_PREFIXES = ("/api/v1/auth/", "/api/v1/billing/")

# Mirrors apps.platform.models.SaasStatus.PENDING — common/ must not import apps.
SAAS_PENDING = "PENDING"


class BusinessSuspended(PermissionDenied):
    default_detail = "Your business account is suspended. Please contact support."
    error_code = "BUSINESS_SUSPENDED"


class PaymentRequired(PermissionDenied):
    default_detail = "Complete your first MessDeck payment to start using the app."
    error_code = "PAYMENT_REQUIRED"


def saas_status(business):
    """The business's SaaS billing status, or None when it has no billing row."""
    sub = getattr(business, "saas_subscription", None) if business is not None else None
    return sub.status if sub is not None else None


def awaiting_first_payment(business):
    return saas_status(business) == SAAS_PENDING


class TenantJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user = result[0]
        if getattr(user, "role", None) != Role.SUPER_ADMIN and not request.path.startswith(
            LOCKED_ALLOWED_PREFIXES
        ):
            business = getattr(user, "business", None)
            if business is not None:
                if business.status == Status.SUSPENDED:
                    raise BusinessSuspended()
                if awaiting_first_payment(business):
                    raise PaymentRequired()
        return result
