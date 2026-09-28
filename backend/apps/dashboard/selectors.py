"""Dashboard aggregator (DB-01). Owns no data — reads via other apps' models."""

import datetime
from datetime import timedelta
from decimal import Decimal

from django.db import models

from apps.customers.models import Customer
from apps.deliveries.models import Delivery, DeliveryStatus
from apps.payments.models import Payment, PaymentStatus
from apps.subscriptions.models import Subscription
from common.constants import SubStatus


def get_dashboard_data(business_id):
    """Aggregate all KPIs for the dashboard in one call."""
    today = datetime.date.today()
    month_start = today.replace(day=1)

    # Customers
    customer_qs = Customer.objects.filter(business_id=business_id)
    active_customers = customer_qs.filter(status="ACTIVE").count()
    new_customers_this_month = customer_qs.filter(created_at__date__gte=month_start).count()

    # Subscriptions
    sub_qs = Subscription.objects.filter(business_id=business_id)
    active_subs = sub_qs.filter(status=SubStatus.ACTIVE).count()
    expiring_today = sub_qs.filter(status=SubStatus.ACTIVE, end_date=today).count()
    expiring_3_days = sub_qs.filter(
        status=SubStatus.ACTIVE, end_date__gte=today, end_date__lte=today + timedelta(days=3)
    ).count()
    expiring_week = sub_qs.filter(
        status=SubStatus.ACTIVE, end_date__gte=today, end_date__lte=today + timedelta(days=7)
    ).count()
    expired_count = sub_qs.filter(status=SubStatus.EXPIRED).count()
    pending_subs = sub_qs.filter(status=SubStatus.PENDING).count()

    # Deliveries today
    delivery_qs = Delivery.objects.filter(business_id=business_id, delivery_date=today)
    total_deliveries_today = delivery_qs.count()
    delivered_today = delivery_qs.filter(status=DeliveryStatus.DELIVERED).count()
    pending_deliveries_today = delivery_qs.filter(
        status__in=[DeliveryStatus.PENDING, DeliveryStatus.OUT_FOR_DELIVERY]
    ).count()

    # Meals today (by type)
    meals_today = list(
        delivery_qs.filter(
            status__in=[DeliveryStatus.PENDING, DeliveryStatus.OUT_FOR_DELIVERY, DeliveryStatus.DELIVERED]
        )
        .values("meal__name")
        .annotate(count=models.Count("id"))
        .order_by("meal__name")
    )

    # Payments
    paid_qs = Payment.objects.filter(business_id=business_id, status=PaymentStatus.PAID)
    today_revenue = paid_qs.filter(payment_date=today).aggregate(total=models.Sum("amount"))[
        "total"
    ] or Decimal("0.00")
    month_revenue = paid_qs.filter(payment_date__gte=month_start).aggregate(total=models.Sum("amount"))[
        "total"
    ] or Decimal("0.00")
    total_pending_amount = sub_qs.filter(
        status__in=[SubStatus.PENDING, SubStatus.ACTIVE, SubStatus.PAUSED]
    ).aggregate(total=models.Sum("pending_amount"))["total"] or Decimal("0.00")

    return {
        "customers": {
            "active": active_customers,
            "new_this_month": new_customers_this_month,
        },
        "subscriptions": {
            "active": active_subs,
            "pending": pending_subs,
            "expiring_today": expiring_today,
            "expiring_3_days": expiring_3_days,
            "expiring_week": expiring_week,
            "expired": expired_count,
        },
        "deliveries": {
            "total_today": total_deliveries_today,
            "delivered": delivered_today,
            "pending": pending_deliveries_today,
        },
        "meals_today": meals_today,
        "payments": {
            "today_revenue": today_revenue,
            "month_revenue": month_revenue,
            "total_pending": total_pending_amount,
        },
    }
