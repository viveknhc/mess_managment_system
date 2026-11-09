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

# Deliveries cancelled by a pause window — hidden from today's operational list
# (the customer isn't expecting a meal; delivery staff shouldn't see them).
PAUSED_DELIVERY_Q = models.Q(status=DeliveryStatus.CANCELLED, pause__isnull=False)


class DeliveryService:
    @staticmethod
    @transaction.atomic
    def generate_delivery_schedule(subscription):
        """Bulk insert PENDING deliveries for the subscription period.

        Idempotent — skips dates that already have a delivery row. Dates inside
        any pause window are never generated. Rows CANCELLED by a *closed* pause
        don't consume the plan's meal quota (they were compensated by extending
        end_date), so the replacement meals land after the original schedule.
        """
        if subscription.status not in (SubStatus.ACTIVE, SubStatus.PENDING):
            return []

        rows = list(
            Delivery.objects.filter(subscription=subscription).values_list(
                "delivery_date", "status", "pause__is_closed"
            )
        )
        existing_dates = {r[0] for r in rows}
        compensated = sum(1 for _d, st, closed in rows if st == DeliveryStatus.CANCELLED and closed)
        remaining_to_create = subscription.plan.total_meals - (len(rows) - compensated)
        windows = list(SubscriptionPause.objects.filter(subscription=subscription))

        deliveries = []
        current = subscription.start_date
        while current <= subscription.end_date and len(deliveries) < remaining_to_create:
            if current not in existing_dates and not any(w.covers(current) for w in windows):
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
    def pause_deliveries(subscription, *, start_date, end_date=None, reason=""):
        """Record a pause window and cancel its PENDING deliveries.

        ``end_date=None`` = open-ended. Validation and subscription status
        changes belong to SubscriptionService.pause — call that instead.
        """
        pause = SubscriptionPause.objects.create(
            business_id=subscription.business_id,
            subscription=subscription,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )
        DeliveryService.cancel_window_deliveries(pause)
        return pause

    @staticmethod
    def cancel_window_deliveries(pause):
        """Cancel PENDING deliveries inside the pause window, tagged with the pause."""
        qs = Delivery.objects.filter(
            subscription_id=pause.subscription_id,
            delivery_date__gte=pause.start_date,
            status=DeliveryStatus.PENDING,
        )
        last = pause.last_paused_day
        if last is not None:
            qs = qs.filter(delivery_date__lte=last)
        return qs.update(status=DeliveryStatus.CANCELLED, pause=pause, updated_at=timezone.now())

    @staticmethod
    @transaction.atomic
    def resume_deliveries(subscription, pause, *, from_date=None):
        """Restore deliveries cancelled by this pause back to PENDING.

        With ``from_date``, only rows on/after it are restored (manual resume
        mid-window); earlier rows stay CANCELLED as paused meals.
        """
        qs = Delivery.objects.filter(subscription=subscription, pause=pause, status=DeliveryStatus.CANCELLED)
        if from_date is not None:
            qs = qs.filter(delivery_date__gte=from_date)
        return qs.update(status=DeliveryStatus.PENDING, pause=None, updated_at=timezone.now())

    @staticmethod
    def end_pause_early(pause, *, on_date):
        """Mark a window as ended by manual resume on ``on_date``."""
        pause.resumed_on = on_date
        pause.save(update_fields=["resumed_on", "updated_at"])
        return pause

    @staticmethod
    def close_pause(pause, *, days_extended):
        """Mark a window finished with the number of days added to end_date."""
        pause.is_closed = True
        pause.days_extended = days_extended
        pause.save(update_fields=["is_closed", "days_extended", "updated_at"])
        return pause


class PauseSelector:
    @staticmethod
    def open_pauses(subscription):
        return list(SubscriptionPause.objects.filter(subscription=subscription, is_closed=False))

    @staticmethod
    def paused_meal_count(pause):
        """Meals not served because of this window (still CANCELLED by it)."""
        return Delivery.objects.filter(pause=pause, status=DeliveryStatus.CANCELLED).count()

    @staticmethod
    def windows_ending_before(day):
        """Open windows whose last paused day is before ``day`` (all tenants)."""
        return SubscriptionPause.objects.filter(is_closed=False, end_date__lt=day).order_by("start_date")

    @staticmethod
    def windows_starting_by(day):
        """Open windows covering ``day`` on ACTIVE subscriptions (all tenants)."""
        return (
            SubscriptionPause.objects.filter(
                is_closed=False,
                start_date__lte=day,
                subscription__status=SubStatus.ACTIVE,
            )
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=day))
            .order_by("start_date")
        )


class DeliverySelector:
    @staticmethod
    def get_today(business_id):
        """Today's deliveries for a business."""
        return (
            Delivery.objects.filter(
                business_id=business_id,
                delivery_date=datetime.date.today(),
            )
            .exclude(PAUSED_DELIVERY_Q)
            .select_related("customer", "meal", "assigned_staff")
        )

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
    def get_today_summary(business_id):
        """Today's delivery counts by status — aggregates only, no customer data (kitchen-safe).

        Pause-cancelled rows are excluded (not part of today's workload).
        """
        rows = (
            Delivery.objects.filter(business_id=business_id, delivery_date=datetime.date.today())
            .exclude(PAUSED_DELIVERY_Q)
            .values("status")
            .annotate(count=models.Count("id"))
        )
        by_status = {r["status"]: r["count"] for r in rows}
        return {
            "total": sum(by_status.values()),
            "pending": by_status.get(DeliveryStatus.PENDING, 0)
            + by_status.get(DeliveryStatus.OUT_FOR_DELIVERY, 0),
            "delivered": by_status.get(DeliveryStatus.DELIVERED, 0),
            "not_delivered": by_status.get(DeliveryStatus.NOT_DELIVERED, 0),
            "skipped": by_status.get(DeliveryStatus.SKIPPED, 0),
            "cancelled": by_status.get(DeliveryStatus.CANCELLED, 0),
        }

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
