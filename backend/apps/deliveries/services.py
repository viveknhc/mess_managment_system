"""Delivery, skip, pause business logic (D-03, D-04, D-08, D-10, D-11)."""

import datetime
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone

from apps.deliveries.models import (
    Delivery,
    DeliveryStatus,
    MealSkip,
    SubscriptionPause,
)
from apps.subscriptions.models import Subscription
from common.constants import SubStatus


class DeliveryService:
    @staticmethod
    @transaction.atomic
    def generate_delivery_schedule(subscription):
        """Bulk insert PENDING deliveries for the subscription period.

        Idempotent — skips dates that already have a delivery row.
        """
        if subscription.status not in (SubStatus.ACTIVE, SubStatus.PENDING):
            return []

        existing_dates = set(
            Delivery.objects.filter(subscription=subscription).values_list("delivery_date", flat=True)
        )
        remaining_to_create = subscription.plan.total_meals - len(existing_dates)

        deliveries = []
        current = subscription.start_date
        while current <= subscription.end_date and len(deliveries) < remaining_to_create:
            if current not in existing_dates:
                deliveries.append(
                    Delivery(
                        business_id=subscription.business_id,
                        subscription=subscription,
                        customer=subscription.customer,
                        meal=subscription.plan.meal,
                        delivery_date=current,
                        status=DeliveryStatus.PENDING,
                    )
                )
            current += timedelta(days=1)

        if deliveries:
            Delivery.objects.bulk_create(deliveries, ignore_conflicts=True)
        return deliveries

    @staticmethod
    @transaction.atomic
    def update_status(delivery, new_status, *, notes=""):
        """Transition a delivery to a new status."""
        if not delivery.can_transition_to(new_status):
            raise ValueError(f"Cannot transition delivery from {delivery.status} to {new_status}")
        delivery.status = new_status
        if notes:
            delivery.notes = notes
        if new_status == DeliveryStatus.DELIVERED:
            delivery.delivered_at = timezone.now()
        delivery.save(update_fields=["status", "notes", "delivered_at", "updated_at"])
        return delivery

    @staticmethod
    @transaction.atomic
    def skip_meal(delivery, *, reason=""):
        """Skip a specific delivery. Creates a MealSkip record.

        Default rule: NONE (no adjustment). Settings module will add EXTEND/CREDIT.
        """
        if delivery.status != DeliveryStatus.PENDING:
            raise ValueError(f"Can only skip PENDING deliveries, got {delivery.status}")

        delivery.status = DeliveryStatus.SKIPPED
        delivery.save(update_fields=["status", "updated_at"])

        skip = MealSkip.objects.create(
            business_id=delivery.business_id,
            subscription=delivery.subscription,
            customer=delivery.customer,
            delivery=delivery,
            skip_date=delivery.delivery_date,
            reason=reason,
        )
        return skip

    @staticmethod
    @transaction.atomic
    def pause_deliveries(subscription, *, start_date, end_date, reason=""):
        """Pause deliveries in a date range. Creates SubscriptionPause record."""
        # Cancel pending deliveries in range
        Delivery.objects.filter(
            subscription=subscription,
            delivery_date__gte=start_date,
            delivery_date__lte=end_date,
            status=DeliveryStatus.PENDING,
        ).update(status=DeliveryStatus.CANCELLED)

        pause = SubscriptionPause.objects.create(
            business_id=subscription.business_id,
            subscription=subscription,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )
        return pause

    @staticmethod
    @transaction.atomic
    def resume_deliveries(subscription, pause):
        """Restore cancelled deliveries from a pause period back to PENDING."""
        Delivery.objects.filter(
            subscription=subscription,
            delivery_date__gte=pause.start_date,
            delivery_date__lte=pause.end_date,
            status=DeliveryStatus.CANCELLED,
        ).update(status=DeliveryStatus.PENDING)


class DeliverySelector:
    @staticmethod
    def get_today(business_id):
        """Today's deliveries for a business."""
        return Delivery.objects.filter(
            business_id=business_id,
            delivery_date=datetime.date.today(),
        ).select_related("customer", "meal", "assigned_staff")

    @staticmethod
    def get_kitchen_counts(business_id):
        """Today's meal totals per meal type — for kitchen staff."""
        today = datetime.date.today()
        return (
            Delivery.objects.filter(
                business_id=business_id,
                delivery_date=today,
                status__in=[DeliveryStatus.PENDING, DeliveryStatus.OUT_FOR_DELIVERY],
            )
            .values("meal__name")
            .annotate(count=models.Count("id"))
            .order_by("meal__name")
        )

    @staticmethod
    def expire_subscriptions():
        """Nightly sweep: mark ACTIVE subscriptions past end_date as EXPIRED."""
        today = datetime.date.today()
        expired = Subscription.objects.filter(
            status=SubStatus.ACTIVE,
            end_date__lt=today,
        )
        count = expired.update(status=SubStatus.EXPIRED)
        return count
