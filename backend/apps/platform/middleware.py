"""Quota enforcement — blocks resource creation when plan limits are reached.

Called from TenantScopedViewSet.perform_create() — not a Django middleware
because JWT auth isn't available at middleware level.
"""

import logging

from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

# (model_label, limit_field)
QUOTA_MAP = {
    "customers.Customer": "max_customers",
    "accounts.User": "max_staff",
}


def _counted(label, model_class, business):
    """Rows that use up a seat: active staff logins (not the owner, not customers' portal
    logins); customers who haven't been removed."""
    from common.constants import Role, Status

    qs = model_class.objects.filter(business=business)
    if label == "accounts.User":
        return qs.filter(role__in=[Role.MANAGER, Role.DELIVERY_STAFF, Role.KITCHEN_STAFF], is_active=True)
    if label == "customers.Customer":
        return qs.exclude(status=Status.INACTIVE)
    return qs


class QuotaError(APIException):
    status_code = 402
    default_detail = "Plan quota exceeded."
    default_code = "QUOTA_EXCEEDED"


def check_quota(business, model_class):
    """Check if business has hit its plan quota for the given model.

    Raises QuotaError (402) if limit reached.
    No-ops for trial (no plan), unlimited (limit=0), or no subscription.
    """
    try:
        sub = business.saas_subscription
    except Exception:
        return  # No subscription — bootstrap phase, allow

    if not sub.plan:
        return  # Trial with no plan — no limits

    label = f"{model_class._meta.app_label}.{model_class.__name__}"
    limit_field = QUOTA_MAP.get(label)
    if not limit_field:
        return

    limit = getattr(sub.plan, limit_field, 0)
    if limit == 0:
        return  # unlimited

    current_count = _counted(label, model_class, business).count()
    if current_count >= limit:
        resource = limit_field.replace("max_", "")
        raise QuotaError(f"Your plan allows a maximum of {limit} {resource}. Please upgrade your plan.")
