"""Subscription business logic (S-04, S-06, S-07, S-08, S-09).

Thin views call these; all writes happen here inside transactions.
"""

import datetime
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.settings_app.services import KitchenCalendar
from apps.subscriptions.models import Subscription, SubscriptionItem
from common.constants import Status, SubStatus

MAX_ITEMS = 20


def _clean_items(items):
    """[{label, price_per_meal}] → [(label, Decimal)], blanks dropped, validated."""
    cleaned = []
    for item in items or []:
        label = " ".join(str(item.get("label", "")).split())
        if not label:
            continue
        price = Decimal(str(item.get("price_per_meal") or "0"))
        if price < 0:
            raise ValueError(f'"{label}": price per meal cannot be negative.')
        cleaned.append((label[:120], price.quantize(Decimal("0.01"))))
    if len(cleaned) > MAX_ITEMS:
        raise ValueError(f"At most {MAX_ITEMS} customizations per subscription.")
    return cleaned


def _extras_per_meal(items):
    return sum((price for _label, price in items), Decimal("0.00"))


def _price_for(plan, custom_price, items, meals):
    """Subscription total: the agreed base price plus each extra × meals."""
    base = plan.price if custom_price is None else custom_price
    return (base + _extras_per_meal(items) * meals).quantize(Decimal("0.01"))


def _write_items(subscription, items):
    SubscriptionItem.objects.filter(subscription=subscription).delete()
    SubscriptionItem.objects.bulk_create(
        SubscriptionItem(
            business_id=subscription.business_id,
            subscription=subscription,
            label=label,
            price_per_meal=price,
            position=i,
        )
        for i, (label, price) in enumerate(items)
    )


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
        calendar = KitchenCalendar.for_business(subscription.business_id)
        subscription.end_date = calendar.add_open_days(max(subscription.end_date, last), paused_meals)
        fields.append("end_date")
    DeliveryService.close_pause(pause, days_extended=paused_meals if "end_date" in fields else 0)

    still_paused = any(p.covers(today) for p in PauseSelector.open_pauses(subscription))
    if subscription.status == SubStatus.PAUSED and not still_paused:
        subscription.transition_to(SubStatus.ACTIVE)
        fields.append("status")
    if fields:
        subscription.save(update_fields=[*fields, "updated_at"])
    DeliveryService.generate_delivery_schedule(subscription)


def _lock_customer(customer):
    from apps.customers.models import Customer

    Customer.objects.select_for_update().filter(pk=customer.pk).first()


def _start_late_from_today(subscription, today):
    """A subscription activated after its start date starts today instead, keeping its
    length — otherwise the days before payment (or all of them) would be lost.

    Only when it was created for today or a later date. A subscription the owner entered
    with a start date already in the past (moving an existing customer into MessDeck)
    keeps the dates they chose.
    """
    created_on = timezone.localdate(subscription.created_at) if subscription.created_at else today
    backdated = subscription.start_date < created_on
    if subscription.start_date < today and not backdated:
        length = subscription.end_date - subscription.start_date
        subscription.start_date = today
        subscription.end_date = today + length
        return True
    return False


def _activate_if_free(subscription):
    """A ₹0 plan needs no payment: activate straight away and schedule deliveries."""
    from apps.deliveries.services import DeliveryService

    if subscription.total_amount > 0:
        return subscription
    _start_late_from_today(subscription, datetime.date.today())
    subscription.transition_to(SubStatus.ACTIVE)
    subscription.save(update_fields=["status", "start_date", "end_date", "updated_at"])
    DeliveryService.generate_delivery_schedule(subscription)
    return subscription


class SubscriptionService:
    @staticmethod
    def refresh_remaining_meals(subscription):
        """Meals still owed = plan meals − meals used. A meal is used when it went out
        (delivered or not delivered) or was skipped without the end date being extended.
        Ended subscriptions owe nothing."""
        from apps.deliveries.models import Delivery, DeliveryStatus, SkipAdjustment

        if subscription.status in (SubStatus.CANCELLED, SubStatus.EXPIRED):
            remaining = 0
        else:
            rows = Delivery.objects.filter(subscription=subscription)
            went_out = rows.filter(
                status__in=[
                    DeliveryStatus.OUT_FOR_DELIVERY,
                    DeliveryStatus.DELIVERED,
                    DeliveryStatus.NOT_DELIVERED,
                ]
            ).count()
            skipped = rows.filter(status=DeliveryStatus.SKIPPED)
            extended = skipped.filter(skip_record__adjustment=SkipAdjustment.EXTEND).distinct().count()
            remaining = max(subscription.total_meals - went_out - (skipped.count() - extended), 0)
        Subscription.objects.filter(pk=subscription.pk).update(remaining_meals=remaining)
        subscription.remaining_meals = remaining
        return remaining

    @staticmethod
    def activate_on_full_payment(subscription, today=None):
        """PENDING → ACTIVE once fully paid (caller holds the row lock and saves).
        Returns the fields changed."""
        subscription.transition_to(SubStatus.ACTIVE)
        fields = ["status"]
        if _start_late_from_today(subscription, today or datetime.date.today()):
            fields += ["start_date", "end_date"]
        return fields

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
    def create_subscription(*, business_id, customer, plan, start_date, custom_price=None, items=None):
        """Create a PENDING subscription from a plan.

        Validates customer and plan belong to the same business. ``custom_price`` replaces
        the plan price for this customer; ``items`` ([{label, price_per_meal}]) are food
        customizations, each charged per meal of the plan (feature custom_subscriptions —
        the caller checks it).
        """
        if custom_price is not None and custom_price < 0:
            raise ValueError("Custom price cannot be negative.")
        items = _clean_items(items)
        total = _price_for(plan, custom_price, items, plan.total_meals)
        if customer.business_id != business_id:
            raise ValueError("Customer does not belong to this business.")
        if customer.status != Status.ACTIVE:
            raise ValueError(
                f"{customer.name} is {customer.get_status_display().lower()}. Make them active first."
            )
        if plan.business_id != business_id:
            raise ValueError("Plan does not belong to this business.")
        if not plan.is_active:
            raise ValueError("Cannot subscribe to an inactive plan.")

        end_date = KitchenCalendar.for_business(business_id).plan_end_date(
            start_date, plan.duration_days, plan.total_meals
        )

        _lock_customer(customer)  # a double-submitted create waits here, then sees the first one
        SubscriptionService.ensure_no_overlap(customer, plan, start_date, end_date)

        subscription = Subscription.objects.create(
            business_id=business_id,
            customer=customer,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            status=SubStatus.PENDING,
            total_amount=total,
            paid_amount=Decimal("0.00"),
            pending_amount=total,
            remaining_meals=plan.total_meals,
            meal=plan.meal,
            total_meals=plan.total_meals,
            custom_price=custom_price,
        )
        _write_items(subscription, items)
        return _activate_if_free(subscription)

    @staticmethod
    @transaction.atomic
    def customize(subscription, *, items, custom_price=..., today=None):
        """Change a live subscription's food customizations (and, before it starts, its price).

        - PENDING: total = (custom_price or plan price) + extras × plan meals. If what's
          already paid now covers it, the subscription activates like a full payment.
        - ACTIVE / PAUSED: the price is fixed; a change in extras is charged (or credited)
          for the meals still to come, so a new +₹20 extra adds ₹20 × meals left to pending.
          It can't drop the total below what the customer already paid.
        - EXPIRED / CANCELLED: nothing to change.

        ``custom_price`` omitted = keep the current one; None = back to the plan price.
        """
        from apps.deliveries.services import DeliveryService

        _lock(subscription)
        status_ = subscription.status
        if status_ in (SubStatus.EXPIRED, SubStatus.CANCELLED):
            raise ValueError(f"A {status_.lower()} subscription can't be changed. Renew it instead.")
        new_items = _clean_items(items)
        old_items = [(i.label, i.price_per_meal) for i in subscription.items.all()]

        if status_ == SubStatus.PENDING:
            if custom_price is not ...:
                if custom_price is not None and custom_price < 0:
                    raise ValueError("Custom price cannot be negative.")
                subscription.custom_price = custom_price
            new_total = _price_for(
                subscription.plan, subscription.custom_price, new_items, subscription.total_meals
            )
        else:
            if custom_price is not ... and custom_price != subscription.custom_price:
                raise ValueError(
                    "The price can only be changed before the subscription starts. "
                    "Extras added now are charged for the meals left."
                )
            delta = (_extras_per_meal(new_items) - _extras_per_meal(old_items)) * subscription.remaining_meals
            new_total = (subscription.total_amount + delta).quantize(Decimal("0.01"))

        if new_total < subscription.paid_amount:
            raise ValueError(
                f"{subscription.customer.name} has already paid ₹{subscription.paid_amount}; "
                f"the new total would be ₹{new_total}."
            )

        subscription.total_amount = new_total
        subscription.pending_amount = new_total - subscription.paid_amount
        fields = ["custom_price", "total_amount", "pending_amount", "updated_at"]
        activated = status_ == SubStatus.PENDING and subscription.pending_amount == 0
        if activated:
            fields += SubscriptionService.activate_on_full_payment(subscription, today=today)
        subscription.save(update_fields=fields)
        _write_items(subscription, new_items)
        if activated:
            DeliveryService.generate_delivery_schedule(subscription)
        return subscription

    # ── Pause / resume (D-10) ────────────────────────────────────────────
    #
    # A pause is a window [start_date, end_date] (end_date None = open-ended)
    # recorded as deliveries.SubscriptionPause. Deliveries in the window are
    # CANCELLED and tagged with the pause so they can be restored. The
    # subscription is PAUSED only while today is inside the window; a future
    # window leaves it ACTIVE until process_pause_windows() flips it.
    #
    # End-date rule: there is no pause extension point yet (only ``skip``), so
    # paused days always EXTEND the subscription — when a window closes,
    # end_date = max(end_date, last paused day) + number of meals the window
    # actually cancelled (counted in days the kitchen is open), and the
    # replacement deliveries are generated.

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
        if end_date is not None:
            calendar = KitchenCalendar.for_business(subscription.business_id)
            if calendar.weekly_off_days and calendar.nth_open_day(start_date, 1) > end_date:
                raise PauseValidationError(
                    "The kitchen is closed on those days, so there are no meals to pause."
                )

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
    def extend_end_date(subscription, *, days):
        """Push end_date out by ``days`` open kitchen days (e.g. a skip policy compensating a meal)."""
        _lock(subscription)
        calendar = KitchenCalendar.for_business(subscription.business_id)
        subscription.end_date = calendar.add_open_days(subscription.end_date, days)
        subscription.save(update_fields=["end_date", "updated_at"])
        return subscription

    @staticmethod
    @transaction.atomic
    def apply_kitchen_calendar(business_id, *, today=None):
        """Re-fit live subscriptions after the mess changes the days its kitchen is closed.

        Upcoming PENDING deliveries on closed days are removed and re-placed on open days
        at the end of the schedule (meals are kept, end_date moves later). Unpaid
        subscriptions get the end date a new one would get. Returns how many changed.
        """
        from apps.deliveries.services import DeliveryService

        today = today or datetime.date.today()
        calendar = KitchenCalendar.for_business(business_id)
        live = Subscription.objects.filter(
            business_id=business_id, status__in=[SubStatus.PENDING, SubStatus.ACTIVE, SubStatus.PAUSED]
        ).values_list("pk", flat=True)
        changed = 0
        for pk in list(live):
            sub = _lock(Subscription.objects.get(pk=pk))
            before = sub.end_date
            if sub.status == SubStatus.PENDING:
                fits = calendar.nth_open_day(sub.start_date, sub.total_meals)
                if fits > sub.end_date:
                    sub.end_date = fits
                    sub.save(update_fields=["end_date", "updated_at"])
            removed = DeliveryService.remove_closed_day_deliveries(sub, from_date=today, calendar=calendar)
            if removed:
                DeliveryService.generate_delivery_schedule(sub)
            changed += bool(removed or sub.end_date != before)
        return changed

    @staticmethod
    @transaction.atomic
    def cancel(subscription, *, today=None):
        """Cancel a subscription and stop its service.

        Row-locked (so a payment can't land at the same moment), then every PENDING
        delivery from today on is cancelled and open pause windows are closed without
        extending anything — nothing is cooked or delivered for a cancelled subscription.
        """
        from apps.deliveries.services import DeliveryService, PauseSelector

        today = today or datetime.date.today()
        _lock(subscription)
        subscription.transition_to(SubStatus.CANCELLED)
        subscription.save(update_fields=["status", "updated_at"])
        DeliveryService.cancel_upcoming_deliveries(subscription, from_date=today)
        for pause in PauseSelector.open_pauses(subscription):
            DeliveryService.close_pause(pause, days_extended=0)
        SubscriptionService.refresh_remaining_meals(subscription)
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
        customer = subscription.customer
        if customer.status != Status.ACTIVE:
            raise ValueError(
                f"{customer.name} is {customer.get_status_display().lower()}. Make them active first."
            )

        new_start = start_date or datetime.date.today()
        new_end = KitchenCalendar.for_business(subscription.business_id).plan_end_date(
            new_start, plan.duration_days, plan.total_meals
        )
        _lock_customer(customer)
        SubscriptionService.ensure_no_overlap(customer, plan, new_start, new_end)

        # The customer keeps their agreed price and food customizations.
        items = [(i.label, i.price_per_meal) for i in subscription.items.all()]
        total = _price_for(plan, subscription.custom_price, items, plan.total_meals)
        renewal = Subscription.objects.create(
            business_id=subscription.business_id,
            customer=subscription.customer,
            plan=plan,
            start_date=new_start,
            end_date=new_end,
            status=SubStatus.PENDING,
            total_amount=total,
            paid_amount=Decimal("0.00"),
            pending_amount=total,
            remaining_meals=plan.total_meals,
            meal=plan.meal,
            total_meals=plan.total_meals,
            renewed_from=subscription,
            custom_price=subscription.custom_price,
        )
        _write_items(renewal, items)
        return _activate_if_free(renewal)


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
