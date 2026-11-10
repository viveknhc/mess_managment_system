"""Subscription business logic (S-04, S-06, S-07, S-08, S-09).

Thin views call these; all writes happen here inside transactions.
"""

import datetime
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from apps.subscriptions.models import Subscription
from common.constants import SubStatus


class PauseValidationError(ValueError):
    """Bad pause request (dates/overlap) — distinct from an illegal transition."""


def _lock(subscription):
    """Row-lock the subscription and refresh the given instance in place."""
    Subscription.objects.select_for_update().filter(pk=subscription.pk).first()
    subscription.refresh_from_db()
    return subscription


def _close_window(subscription, pause, today):
    """Finish a pause window: extend end_date by its paused meals, reactivate,
    and generate replacement deliveries. Caller holds the subscription lock."""
    from apps.deliveries.services import DeliveryService, PauseSelector

    paused_meals = PauseSelector.paused_meal_count(pause)
    fields = []
    if paused_meals and subscription.status in (SubStatus.ACTIVE, SubStatus.PAUSED):
        last = pause.last_paused_day or today - timedelta(days=1)
        subscription.end_date = max(subscription.end_date, last) + timedelta(days=paused_meals)
        fields.append("end_date")
    DeliveryService.close_pause(pause, days_extended=paused_meals if "end_date" in fields else 0)

    still_paused = any(p.covers(today) for p in PauseSelector.open_pauses(subscription))
    if subscription.status == SubStatus.PAUSED and not still_paused:
        subscription.transition_to(SubStatus.ACTIVE)
        fields.append("status")
    if fields:
        subscription.save(update_fields=[*fields, "updated_at"])
    DeliveryService.generate_delivery_schedule(subscription)


class SubscriptionService:
    @staticmethod
    def ensure_no_overlap(customer, plan, start_date, end_date):
        """One live subscription per customer per plan for any given day. A different plan
        (e.g. lunch + dinner) may overlap; the same plan must start after the current one ends."""
        clash = (
            Subscription.objects.filter(
                customer=customer,
                plan=plan,
                status__in=[SubStatus.PENDING, SubStatus.ACTIVE, SubStatus.PAUSED],
                start_date__lte=end_date,
                end_date__gte=start_date,
            )
            .order_by("-end_date")
            .first()
        )
        if clash:
            unpaid = " and isn't paid yet" if clash.status == SubStatus.PENDING else ""
            raise ValueError(
                f"{customer.name} already has {plan.name} from {clash.start_date:%d %b %Y} to "
                f"{clash.end_date:%d %b %Y} ({clash.get_status_display().lower()}{unpaid}). "
                f"Start the new one after {clash.end_date:%d %b %Y}, or cancel the existing one first."
            )

    @staticmethod
    @transaction.atomic
    def create_subscription(*, business_id, customer, plan, start_date):
        """Create a PENDING subscription from a plan.

        Validates customer and plan belong to the same business.
        """
        if customer.business_id != business_id:
            raise ValueError("Customer does not belong to this business.")
        if plan.business_id != business_id:
            raise ValueError("Plan does not belong to this business.")
        if not plan.is_active:
            raise ValueError("Cannot subscribe to an inactive plan.")

        end_date = start_date + timedelta(days=plan.duration_days)

        SubscriptionService.ensure_no_overlap(customer, plan, start_date, end_date)

        return Subscription.objects.create(
            business_id=business_id,
            customer=customer,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            status=SubStatus.PENDING,
            total_amount=plan.price,
            paid_amount=Decimal("0.00"),
            pending_amount=plan.price,
            remaining_meals=plan.total_meals,
        )

    # ── Pause / resume (D-10) ────────────────────────────────────────────
    #
    # A pause is a window [start_date, end_date] (end_date None = open-ended)
    # recorded as deliveries.SubscriptionPause. Deliveries in the window are
    # CANCELLED and tagged with the pause so they can be restored. The
    # subscription is PAUSED only while today is inside the window; a future
    # window leaves it ACTIVE until process_pause_windows() flips it.
    #
    # End-date rule: BusinessSettings has no pause rule (only skip_rule), so
    # paused days always EXTEND the subscription — when a window closes,
    # end_date = max(end_date, last paused day) + number of meals the window
    # actually cancelled, and the replacement deliveries are generated.

    @staticmethod
    @transaction.atomic
    def pause(subscription, *, start_date=None, end_date=None, reason="", today=None):
        """Pause an ACTIVE subscription for a window starting today or later.

        Raises ValueError on an illegal transition and PauseValidationError
        on bad dates / overlapping windows.
        """
        from apps.deliveries.services import DeliveryService, PauseSelector

        today = today or datetime.date.today()
        _lock(subscription)
        if not subscription.can_transition_to(SubStatus.PAUSED):
            raise ValueError(f"Cannot transition from {subscription.status} to {SubStatus.PAUSED}")

        start_date = start_date or today
        if start_date < today:
            raise PauseValidationError("Pause start date cannot be in the past.")
        if end_date is not None and end_date < start_date:
            raise PauseValidationError("end_date cannot be before start_date.")
        if start_date > subscription.end_date:
            raise PauseValidationError("Pause must start on or before the subscription end date.")
        if any(p.overlaps(start_date, end_date) for p in PauseSelector.open_pauses(subscription)):
            raise PauseValidationError("This pause overlaps an existing pause on the subscription.")

        DeliveryService.pause_deliveries(
            subscription, start_date=start_date, end_date=end_date, reason=reason
        )
        if start_date <= today:
            subscription.transition_to(SubStatus.PAUSED)
            subscription.save(update_fields=["status", "updated_at"])
        return subscription

    @staticmethod
    @transaction.atomic
    def resume(subscription, *, today=None):
        """Resume a PAUSED subscription now.

        Ends every started window today, restores deliveries from today on,
        and extends end_date by the meals that were actually paused.
        """
        from apps.deliveries.services import DeliveryService, PauseSelector

        today = today or datetime.date.today()
        _lock(subscription)
        # Resume is PAUSED → ACTIVE only (PENDING → ACTIVE is reserved for full payment).
        if subscription.status != SubStatus.PAUSED:
            raise ValueError(f"Cannot resume a {subscription.status} subscription (must be PAUSED)")

        for pause in PauseSelector.open_pauses(subscription):
            if pause.start_date > today:
                continue  # future window stays scheduled
            DeliveryService.end_pause_early(pause, on_date=today)
            DeliveryService.resume_deliveries(subscription, pause, from_date=today)
            _close_window(subscription, pause, today)

        if subscription.status == SubStatus.PAUSED:  # legacy pause with no window record
            subscription.transition_to(SubStatus.ACTIVE)
            subscription.save(update_fields=["status", "updated_at"])
        return subscription

    @staticmethod
    def process_pause_windows(today=None):
        """Daily sweep (all tenants): close ended windows, start due ones.

        - Window whose end_date < today → close: extend end_date, PAUSED → ACTIVE,
          generate replacement deliveries.
        - Window covering today on an ACTIVE subscription → ACTIVE → PAUSED.

        Idempotent; each window is handled in its own transaction.
        """
        from apps.deliveries.services import DeliveryService, PauseSelector

        today = today or datetime.date.today()
        ended = started = 0

        for pause in PauseSelector.windows_ending_before(today):
            with transaction.atomic():
                sub = _lock(pause.subscription)
                pause.refresh_from_db()
                if pause.is_closed:
                    continue
                _close_window(sub, pause, today)
                ended += 1

        for pause in PauseSelector.windows_starting_by(today):
            with transaction.atomic():
                sub = _lock(pause.subscription)
                if sub.status != SubStatus.ACTIVE:
                    continue
                DeliveryService.cancel_window_deliveries(pause)
                sub.transition_to(SubStatus.PAUSED)
                sub.save(update_fields=["status", "updated_at"])
                started += 1

        return {"started": started, "ended": ended}

    @staticmethod
    @transaction.atomic
    def cancel(subscription):
        """Cancel a PENDING or ACTIVE subscription."""
        subscription.transition_to(SubStatus.CANCELLED)
        subscription.save(update_fields=["status", "updated_at"])
        return subscription

    @staticmethod
    @transaction.atomic
    def renew(subscription, *, start_date=None):
        """Renew an EXPIRED or CANCELLED subscription.

        Creates a new PENDING subscription linked via renewed_from.
        The old subscription is untouched.
        """
        if subscription.status not in (SubStatus.EXPIRED, SubStatus.CANCELLED):
            raise ValueError(f"Can only renew EXPIRED or CANCELLED subscriptions, got {subscription.status}")

        plan = subscription.plan
        if not plan.is_active:
            raise ValueError("Cannot renew with an inactive plan.")

        new_start = start_date or datetime.date.today()
        new_end = new_start + timedelta(days=plan.duration_days)
        SubscriptionService.ensure_no_overlap(subscription.customer, plan, new_start, new_end)

        return Subscription.objects.create(
            business_id=subscription.business_id,
            customer=subscription.customer,
            plan=plan,
            start_date=new_start,
            end_date=new_end,
            status=SubStatus.PENDING,
            total_amount=plan.price,
            paid_amount=Decimal("0.00"),
            pending_amount=plan.price,
            remaining_meals=plan.total_meals,
            renewed_from=subscription,
        )


class SubscriptionSelector:
    @staticmethod
    def get_expiring(business_id, days_ahead=3):
        """EXPIRING = ACTIVE and end_date within N days. Never stored."""
        today = datetime.date.today()
        return Subscription.objects.filter(
            Q(business_id=business_id)
            & Q(status=SubStatus.ACTIVE)
            & Q(end_date__gte=today)
            & Q(end_date__lte=today + timedelta(days=days_ahead))
        )
