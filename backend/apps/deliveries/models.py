"""Delivery, MealSkip, SubscriptionPause models (D-01, D-07)."""

from datetime import timedelta

from django.db import models

from common.models import TenantScopedModel


class DeliveryStatus:
    PENDING = "PENDING"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    NOT_DELIVERED = "NOT_DELIVERED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


DELIVERY_STATUS_CHOICES = [
    (DeliveryStatus.PENDING, "Pending"),
    (DeliveryStatus.OUT_FOR_DELIVERY, "Out for Delivery"),
    (DeliveryStatus.DELIVERED, "Delivered"),
    (DeliveryStatus.NOT_DELIVERED, "Not Delivered"),
    (DeliveryStatus.SKIPPED, "Skipped"),
    (DeliveryStatus.CANCELLED, "Cancelled"),
]

# Staff can transition deliveries through these paths
DELIVERY_TRANSITIONS = {
    DeliveryStatus.PENDING: [
        DeliveryStatus.OUT_FOR_DELIVERY,
        DeliveryStatus.DELIVERED,
        DeliveryStatus.NOT_DELIVERED,
        DeliveryStatus.SKIPPED,
        DeliveryStatus.CANCELLED,
    ],
    DeliveryStatus.OUT_FOR_DELIVERY: [DeliveryStatus.DELIVERED, DeliveryStatus.NOT_DELIVERED],
    DeliveryStatus.DELIVERED: [],
    DeliveryStatus.NOT_DELIVERED: [],
    DeliveryStatus.SKIPPED: [],
    DeliveryStatus.CANCELLED: [],
}


class Delivery(TenantScopedModel):
    """A single meal delivery for a subscription on a specific date."""

    subscription = models.ForeignKey(
        "subscriptions.Subscription", on_delete=models.CASCADE, related_name="deliveries"
    )
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="deliveries")
    meal = models.ForeignKey("meals.Meal", on_delete=models.PROTECT, related_name="deliveries")
    delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default=DeliveryStatus.PENDING)
    assigned_staff = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_deliveries"
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    # Set when this delivery was CANCELLED by a pause window, so resume can
    # restore exactly these rows (and the extension rule can count them).
    pause = models.ForeignKey(
        "deliveries.SubscriptionPause",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="paused_deliveries",
    )

    class Meta:
        ordering = ["delivery_date", "customer__name"]
        indexes = [
            models.Index(fields=["business", "delivery_date", "status"], name="idx_delivery_biz_date"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "delivery_date", "meal"],
                name="unique_delivery_per_sub_date_meal",
            ),
        ]

    def __str__(self):
        return f"{self.customer} — {self.meal} on {self.delivery_date} ({self.status})"

    def can_transition_to(self, new_status):
        return new_status in DELIVERY_TRANSITIONS.get(self.status, [])


class MealSkip(TenantScopedModel):
    """Record of a skipped meal."""

    subscription = models.ForeignKey(
        "subscriptions.Subscription", on_delete=models.CASCADE, related_name="skips"
    )
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="skips")
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="skip_record")
    skip_date = models.DateField()
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-skip_date"]


class SubscriptionPause(TenantScopedModel):
    """A pause window on a subscription.

    - ``end_date`` NULL = open-ended (owner pause until manual resume).
    - ``resumed_on`` = day a manual resume ended the window early; deliveries
      on/after it were restored.
    - ``is_closed`` = window finished and the end-date extension was applied
      (``days_extended`` paused meals added to the subscription end_date).

    The subscription is PAUSED only while today falls inside an open window;
    the daily sweep (SubscriptionService.process_pause_windows) flips it.
    """

    subscription = models.ForeignKey(
        "subscriptions.Subscription", on_delete=models.CASCADE, related_name="pauses"
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True)
    resumed_on = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    days_extended = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["is_closed", "start_date"], name="idx_pause_open_start"),
        ]

    def __str__(self):
        return f"Pause {self.start_date} → {self.end_date or 'open'} ({self.subscription_id})"

    @property
    def last_paused_day(self):
        """Inclusive last paused day, or None when open-ended."""
        if self.resumed_on is not None:
            early = self.resumed_on - timedelta(days=1)
            return early if self.end_date is None else min(early, self.end_date)
        return self.end_date

    def covers(self, day):
        last = self.last_paused_day
        return self.start_date <= day and (last is None or day <= last)

    def overlaps(self, start, end):
        """True if [start, end] (end None = open) intersects this window."""
        last = self.last_paused_day
        if last is not None and last < self.start_date:
            return False  # voided (resumed on its start day)
        starts_before_my_end = last is None or start <= last
        ends_after_my_start = end is None or end >= self.start_date
        return starts_before_my_end and ends_after_my_start
