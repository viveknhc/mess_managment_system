"""Plan model (P-01). A subscription plan offered by a business."""

from django.core.validators import MinValueValidator
from django.db import models

from common.models import TenantScopedModel


class Plan(TenantScopedModel):
    """A subscription plan (e.g. "Monthly Lunch ₹2500").

    Links to a Meal type. Defines duration, pricing, and skip/pause rules.
    total_meals must be <= duration_days.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    meal = models.ForeignKey(
        "meals.Meal",
        on_delete=models.PROTECT,
        related_name="plans",
    )
    duration_days = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Plan duration in days",
    )
    total_meals = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Total meals included in the plan",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    skip_allowed = models.BooleanField(default=False)
    pause_allowed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "name"],
                name="unique_plan_name_per_business",
            ),
        ]

    def __str__(self):
        return f"{self.name} (₹{self.price})"
