"""Meal model (M-01). Represents a meal type offered by a business."""

from django.db import models

from common.models import TenantScopedModel


class Meal(TenantScopedModel):
    """A meal type (Breakfast, Lunch, Dinner, Snacks, etc.).

    price is nullable — some businesses don't price individual meals
    (they price plans instead).
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "name"],
                name="unique_meal_name_per_business",
            ),
        ]

    def __str__(self):
        return self.name
