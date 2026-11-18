"""SUPER_ADMIN reads across a business's modules — read-only, never writes."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.customers.models import Customer
from apps.customization.registry import EXTENSION_POINTS, FEATURES
from apps.customization.services import FeatureService, PolicyService
from apps.deliveries.services import DeliverySelector
from apps.payments.models import Payment, PaymentStatus
from apps.plans.models import Plan
from apps.settings_app.models import BusinessSettings
from apps.subscriptions.models import Subscription
from common.constants import Role, SubStatus

EXPIRING_DAYS = 3  # same predicate as SubscriptionSelector.get_expiring


def _money(value):
    return f"{Decimal(value or 0):.2f}"


def _features(business):
    resolved = FeatureService.resolve(business.id)
    inherited, _source = FeatureService.inherited(business.id)
    return [
        {
            "key": key,
            "label": FEATURES[key].label,
            "description": FEATURES[key].description,
            "enabled": enabled,
            "source": source,
            "inherited": key in inherited,
        }
        for key, (enabled, source) in resolved.items()
    ]


def _policies(business):
    out = []
    for point_key, (policy_key, params) in PolicyService.selected(business.id).items():
        point = EXTENSION_POINTS[point_key]
        policy = point.policies[policy_key]
        out.append(
            {
                "point": point_key,
                "point_label": point.label,
                "policy": policy_key,
                "policy_label": policy.label,
                "description": policy.description,
                "is_default": policy_key == point.default,
                "params": params,
            }
        )
    return out


def _settings(business):
    s = BusinessSettings.objects.filter(business=business).first()
    if s is None:
        return None
    return {
        "min_pause_days": s.min_pause_days,
        "max_pause_days": s.max_pause_days,
        "delivery_start_time": s.delivery_start_time.isoformat() if s.delivery_start_time else None,
        "delivery_end_time": s.delivery_end_time.isoformat() if s.delivery_end_time else None,
        "notify_on_payment": s.notify_on_payment,
        "notify_on_expiring": s.notify_on_expiring,
        "notify_on_delivery": s.notify_on_delivery,
        "online_payments_enabled": s.online_payments_enabled,
        "razorpay_configured": s.razorpay_configured,  # never the keys themselves
    }


def _team(business):
    users = business.users.exclude(role=Role.CUSTOMER).order_by("role", "name")
    return [
        {
            "id": str(u.id),
            "name": u.name,
            "username": u.username,
            "role": u.role,
            "email": u.email,
            "phone": u.phone,
            "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]


def _customers(business):
    qs = Customer.objects.filter(business=business)
    by_status = dict(qs.values_list("status").annotate(n=Count("id")))
    return {
        "total": qs.count(),
        "by_status": by_status,
        "portal_logins": qs.filter(user__isnull=False).count(),
    }


def _subscriptions(business, today):
    qs = Subscription.objects.filter(business=business)
    by_status = dict(qs.values_list("status").annotate(n=Count("id")))
    expiring = qs.filter(status=SubStatus.ACTIVE, end_date__lte=today + timedelta(days=EXPIRING_DAYS)).count()
    pending = qs.filter(status__in=[SubStatus.PENDING, SubStatus.ACTIVE, SubStatus.PAUSED]).aggregate(
        s=Sum("pending_amount")
    )["s"]
    return {"by_status": by_status, "expiring": expiring, "amount_pending": _money(pending)}


def _payments(business, today):
    paid = Payment.objects.filter(business=business, status=PaymentStatus.PAID)
    return {
        "total_collected": _money(paid.aggregate(s=Sum("amount"))["s"]),
        "last_30_days": _money(
            paid.filter(payment_date__gte=today - timedelta(days=30)).aggregate(s=Sum("amount"))["s"]
        ),
        "count": paid.count(),
    }


def _meal_plans(business):
    plans = (
        Plan.objects.filter(business=business)
        .select_related("meal")
        .annotate(active_subs=Count("subscriptions", filter=Q(subscriptions__status=SubStatus.ACTIVE)))
    )
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "meal": p.meal.name,
            "duration_days": p.duration_days,
            "total_meals": p.total_meals,
            "price": _money(p.price),
            "skip_allowed": p.skip_allowed,
            "pause_allowed": p.pause_allowed,
            "is_active": p.is_active,
            "active_subscriptions": p.active_subs,
        }
        for p in plans.order_by("-is_active", "name")
    ]


def _activity(business, limit=10):
    logs = AuditLog.objects.filter(business=business).select_related("user").order_by("-created_at")[:limit]
    return [
        {
            "action": log.action,
            "entity_type": log.entity_type,
            "description": log.description,
            "user": (log.user.name or log.user.username) if log.user else None,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


def business_overview(business):
    """Everything a SUPER_ADMIN needs to see about one mess, in one response."""
    today = timezone.localdate()
    return {
        "business": {
            "id": str(business.id),
            "name": business.name,
            "phone": business.phone,
            "email": business.email,
            "address": business.address,
            "status": business.status,
            "created_at": business.created_at.isoformat(),
        },
        "features": _features(business),
        "policies": _policies(business),
        "settings": _settings(business),
        "team": _team(business),
        "customers": _customers(business),
        "subscriptions": _subscriptions(business, today),
        "payments": _payments(business, today),
        "deliveries_today": DeliverySelector.get_today_summary(business.id),
        "meal_plans": _meal_plans(business),
        "recent_activity": _activity(business),
    }
