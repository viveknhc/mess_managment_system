"""BusinessSettings model (ST-01). Per-business configuration."""

from django.core.validators import MinValueValidator
from django.db import models

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

    class Meta:
        verbose_name_plural = "business settings"

    def __str__(self):
        return f"Settings for {self.business}"
