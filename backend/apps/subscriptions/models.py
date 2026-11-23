"""Subscription model (S-01). The core entity of the system."""

import datetime

from django.db import models

from common.constants import SUB_STATUS_CHOICES, SUB_TRANSITIONS, SubStatus
from common.models import TenantScopedModel


class Subscription(TenantScopedModel):
    """A customer's subscription to a plan.

    State machine: PENDING → ACTIVE → PAUSED/CANCELLED/EXPIRED.
    EXPIRING is computed (never stored): status=ACTIVE AND end_date <= today+3.
    """

    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey("plans.Plan", on_delete=models.PROTECT, related_name="subscriptions")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=SUB_STATUS_CHOICES, default=SubStatus.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_amount = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_meals = models.PositiveIntegerField()
    # Copied from the plan when the subscription is created, so editing the plan later
    # never changes what an existing subscriber is owed.
    meal = models.ForeignKey("meals.Meal", on_delete=models.PROTECT, related_name="+")
    total_meals = models.PositiveIntegerField()
    renewed_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="renewals"
    )
    # Price agreed with this customer instead of the plan's (feature ``custom_subscriptions``).
    # None = the plan price. Carried over on renewal.
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["business", "status", "end_date"],
                name="idx_sub_biz_status_end",
            ),
            models.Index(fields=["customer"], name="idx_sub_customer"),
        ]

    def __str__(self):
        return f"{self.customer} — {self.plan} ({self.status})"

    def save(self, *args, **kwargs):
        # Snapshot the plan's meal and meal count on first save if the caller didn't.
        if self.meal_id is None:
            self.meal_id = self.plan.meal_id
        if self.total_meals is None:
            self.total_meals = self.plan.total_meals
        super().save(*args, **kwargs)

    @property
    def remaining_days(self):
        delta = (self.end_date - datetime.date.today()).days
        return max(delta, 0)

    @property
    def is_expiring(self):
        """EXPIRING = ACTIVE and end_date within 3 days."""
        if self.status != SubStatus.ACTIVE:
            return False
        return 0 <= self.remaining_days <= 3

    def can_transition_to(self, new_status):
        return new_status in SUB_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status):
        """Validate and apply status transition. Raises ValueError on illegal."""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")
        self.status = new_status


class SubscriptionItem(TenantScopedModel):
    """A per-customer food customization on a subscription, e.g. "Extra chicken 100g"
    (+₹20 per meal) or "No rice" (₹0). Feature ``custom_subscriptions``.

    The kitchen sees today's items in its counts; delivery staff see them on each delivery.
    """

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="items")
    label = models.CharField(max_length=120)
    price_per_meal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"{self.label} (+{self.price_per_meal}/meal)"
