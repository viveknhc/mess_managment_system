"""Delivery, MealSkip, SubscriptionPause models (D-01, D-07)."""

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
    """Record of a subscription pause period."""

    subscription = models.ForeignKey(
        "subscriptions.Subscription", on_delete=models.CASCADE, related_name="pauses"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]
