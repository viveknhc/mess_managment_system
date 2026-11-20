"""JWT authentication that also enforces business access (suspension + unpaid onboarding).

Checked here, not per view, so every endpoint (viewsets, APIViews, portal views) is
covered. A locked business keeps access to auth and billing endpoints so the owner can
still log in and pay.

Two locks:
- business.status == SUSPENDED          → 403 BUSINESS_SUSPENDED
- SaaS billing still PENDING (first payment — setup fee + first month — never made),
  or the free TRIAL a SUPER_ADMIN started has run out (trial_ends_at passed)
                                         → 403 PAYMENT_REQUIRED
During a running TRIAL the business has full access.
A business with no SaasSubscription row (bootstrap / own-software installs) is not locked.
"""

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.constants import Role, Status

LOCKED_ALLOWED_PREFIXES = ("/api/v1/auth/", "/api/v1/billing/")

# Mirror apps.platform.models.SaasStatus — common/ must not import apps.
SAAS_PENDING = "PENDING"
SAAS_TRIAL = "TRIAL"


class BusinessSuspended(PermissionDenied):
    default_detail = "Your business account is suspended. Please contact support."
    error_code = "BUSINESS_SUSPENDED"


class PaymentRequired(PermissionDenied):
    default_detail = "Complete your first MessDeck payment to start using the app."
    error_code = "PAYMENT_REQUIRED"


class TrialEnded(PaymentRequired):
    default_detail = (
        "Your 7-day free trial has ended. Complete your first MessDeck payment to keep using the app."
    )


def _saas_subscription(business):
    return getattr(business, "saas_subscription", None) if business is not None else None


def saas_status(business):
    """The business's SaaS billing status, or None when it has no billing row."""
    sub = _saas_subscription(business)
    return sub.status if sub is not None else None


def trial_ends_at(business):
    """When the business's free trial ends (aware datetime), or None if no trial was started."""
    sub = _saas_subscription(business)
    return sub.trial_ends_at if sub is not None and sub.status == SAAS_TRIAL else None


def awaiting_first_payment(business):
    return saas_status(business) == SAAS_PENDING


def trial_ended(business, now=None):
    ends = trial_ends_at(business)
    return ends is not None and ends <= (now or timezone.now())


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
                if trial_ended(business):
                    raise TrialEnded()
        return result
