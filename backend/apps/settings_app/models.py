"""BusinessSettings model (ST-01). Per-business configuration."""

from django.core.validators import MinValueValidator
from django.db import models

from common import crypto
from common.models import TimeStampedModel, UUIDModel


class SkipRule:
    EXTEND = "EXTEND"
    CREDIT = "CREDIT"
    NONE = "NONE"


SKIP_RULE_CHOICES = [
    (SkipRule.EXTEND, "Extend subscription end date"),
    (SkipRule.CREDIT, "Meal credit"),
    (SkipRule.NONE, "No adjustment"),
]


class BusinessSettings(UUIDModel, TimeStampedModel):
    """Configuration for a business. One row per business (OneToOne)."""

    business = models.OneToOneField("businesses.Business", on_delete=models.CASCADE, related_name="settings")
    max_skip_days = models.PositiveIntegerField(default=3, help_text="Max skip days per subscription")
    min_pause_days = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], help_text="Minimum pause duration in days"
    )
    max_pause_days = models.PositiveIntegerField(default=7, help_text="Maximum pause duration in days")
    skip_rule = models.CharField(max_length=10, choices=SKIP_RULE_CHOICES, default=SkipRule.NONE)
    delivery_start_time = models.TimeField(null=True, blank=True, help_text="Delivery window start")
    delivery_end_time = models.TimeField(null=True, blank=True, help_text="Delivery window end")
    notify_on_payment = models.BooleanField(default=True)
    notify_on_expiring = models.BooleanField(default=True)
    notify_on_delivery = models.BooleanField(default=False)

    # Online payments: customers pay into the business's own Razorpay account
    online_payments_enabled = models.BooleanField(default=False)
    razorpay_key_id = models.CharField(max_length=64, blank=True)
    razorpay_key_secret_encrypted = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "business settings"

    def __str__(self):
        return f"Settings for {self.business}"

    def set_razorpay_secret(self, secret):
        self.razorpay_key_secret_encrypted = crypto.encrypt(secret)

    @property
    def razorpay_configured(self):
        return self.razorpay_keys() is not None

    def razorpay_keys(self):
        """(key_id, key_secret) if saved — used to verify payments even after online payments are switched off."""
        secret = crypto.decrypt(self.razorpay_key_secret_encrypted)
        return (self.razorpay_key_id, secret) if self.razorpay_key_id and secret else None

    def razorpay_credentials(self):
        """(key_id, key_secret) when customers can pay online, else None."""
        return self.razorpay_keys() if self.online_payments_enabled else None
