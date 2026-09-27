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
    renewed_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="renewals"
    )

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
