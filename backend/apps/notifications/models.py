"""Notification model (N-01)."""

from django.db import models
from django.utils import timezone

from common.models import TenantScopedModel


class NotificationType:
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    SUBSCRIPTION_ACTIVATED = "SUBSCRIPTION_ACTIVATED"
    SUBSCRIPTION_EXPIRING = "SUBSCRIPTION_EXPIRING"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    SUBSCRIPTION_RENEWED = "SUBSCRIPTION_RENEWED"
    DELIVERY_UPDATE = "DELIVERY_UPDATE"
    GENERAL = "GENERAL"


NOTIFICATION_TYPE_CHOICES = [
    (NotificationType.PAYMENT_RECEIVED, "Payment Received"),
    (NotificationType.SUBSCRIPTION_ACTIVATED, "Subscription Activated"),
    (NotificationType.SUBSCRIPTION_EXPIRING, "Subscription Expiring"),
    (NotificationType.SUBSCRIPTION_EXPIRED, "Subscription Expired"),
    (NotificationType.SUBSCRIPTION_RENEWED, "Subscription Renewed"),
    (NotificationType.DELIVERY_UPDATE, "Delivery Update"),
    (NotificationType.GENERAL, "General"),
]


class Notification(TenantScopedModel):
    """In-app notification for a user."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(
        max_length=30, choices=NOTIFICATION_TYPE_CHOICES, default=NotificationType.GENERAL
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["user", "is_read"], name="idx_notif_user_read"),
        ]

    def __str__(self):
        return f"{self.title} → {self.user}"
