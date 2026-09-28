"""Report selectors (R-01 to R-05). Read-only aggregations, no models."""

import datetime
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.db.models.functions import ExtractMonth, ExtractYear

from apps.customers.models import Customer
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.payments.models import Payment, PaymentStatus
from apps.subscriptions.models import Subscription
from common.constants import SubStatus


def customer_report(business_id):
    """R-01: Customer counts by status."""
    qs = Customer.objects.filter(business_id=business_id)
    today = datetime.date.today()
    month_start = today.replace(day=1)
    return {
        "total": qs.count(),
        "active": qs.filter(status="ACTIVE").count(),
        "inactive": qs.filter(status="INACTIVE").count(),
        "blocked": qs.filter(status="BLOCKED").count(),
        "new_this_month": qs.filter(created_at__date__gte=month_start).count(),
    }


def subscription_report(business_id):
    """R-02: Subscription counts by status + expiring."""
    qs = Subscription.objects.filter(business_id=business_id)
    today = datetime.date.today()
    return {
        "active": qs.filter(status=SubStatus.ACTIVE).count(),
        "pending": qs.filter(status=SubStatus.PENDING).count(),
        "paused": qs.filter(status=SubStatus.PAUSED).count(),
        "expired": qs.filter(status=SubStatus.EXPIRED).count(),
        "cancelled": qs.filter(status=SubStatus.CANCELLED).count(),
        "expiring_3_days": qs.filter(
            status=SubStatus.ACTIVE, end_date__gte=today, end_date__lte=today + timedelta(days=3)
        ).count(),
        "renewed": qs.filter(renewed_from__isnull=False).count(),
    }


def revenue_report(business_id, *, date_from=None, date_to=None):
    """R-03: Revenue series (daily) + totals."""
    qs = Payment.objects.filter(business_id=business_id, status=PaymentStatus.PAID)
    if date_from:
        qs = qs.filter(payment_date__gte=date_from)
    if date_to:
        qs = qs.filter(payment_date__lte=date_to)

    daily = list(
        qs.values("payment_date")
        .annotate(total=models.Sum("amount"), count=models.Count("id"))
        .order_by("payment_date")
    )

    monthly = list(
        qs.annotate(year=ExtractYear("payment_date"), month=ExtractMonth("payment_date"))
        .values("year", "month")
        .annotate(total=models.Sum("amount"))
        .order_by("year", "month")
    )

    total = qs.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    total_pending = Subscription.objects.filter(
        business_id=business_id, status__in=[SubStatus.PENDING, SubStatus.ACTIVE, SubStatus.PAUSED]
    ).aggregate(total=models.Sum("pending_amount"))["total"] or Decimal("0.00")

    return {
        "daily": daily,
        "monthly": monthly,
        "total_collected": total,
        "total_pending": total_pending,
    }


def meal_report(business_id, *, date_from=None, date_to=None):
    """R-04: Meal delivery counts by type and status."""
    qs = Delivery.objects.filter(business_id=business_id)
    if date_from:
        qs = qs.filter(delivery_date__gte=date_from)
    if date_to:
        qs = qs.filter(delivery_date__lte=date_to)

    by_meal = list(
        qs.values(meal_name=models.F("meal__name"))
        .annotate(
            delivered=models.Count("id", filter=models.Q(status=DeliveryStatus.DELIVERED)),
            skipped=models.Count("id", filter=models.Q(status=DeliveryStatus.SKIPPED)),
            not_delivered=models.Count("id", filter=models.Q(status=DeliveryStatus.NOT_DELIVERED)),
            pending=models.Count("id", filter=models.Q(status=DeliveryStatus.PENDING)),
            total=models.Count("id"),
        )
        .order_by("meal_name")
    )
    return {"by_meal": by_meal}


def payment_report(business_id, *, date_from=None, date_to=None):
    """R-05: Payment details by method and status."""
    qs = Payment.objects.filter(business_id=business_id)
    if date_from:
        qs = qs.filter(payment_date__gte=date_from)
    if date_to:
        qs = qs.filter(payment_date__lte=date_to)

    by_method = list(
        qs.values("method").annotate(total=models.Sum("amount"), count=models.Count("id")).order_by("method")
    )

    by_status = list(
        qs.values("status").annotate(total=models.Sum("amount"), count=models.Count("id")).order_by("status")
    )

    return {"by_method": by_method, "by_status": by_status}
