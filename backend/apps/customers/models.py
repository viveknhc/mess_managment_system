"""Customer model (poc.md §7.3)."""

from django.db import models

from common.constants import Status
from common.models import TenantScopedModel


class Customer(TenantScopedModel):
    """A customer of a mess business.

    customer_code is auto-generated per business (e.g. CUST-0001).
    user FK is nullable — customer may not have a login account yet.
    """

    CUSTOMER_STATUS_CHOICES = [
        (Status.ACTIVE, "Active"),
        (Status.INACTIVE, "Inactive"),
        (Status.BLOCKED, "Blocked"),
    ]

    user = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_profiles",
    )
    customer_code = models.CharField(max_length=20, editable=False)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=CUSTOMER_STATUS_CHOICES,
        default=Status.ACTIVE,
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "customer_code"],
                name="unique_customer_code_per_business",
            ),
        ]
        indexes = [
            models.Index(fields=["business", "name"], name="idx_customer_biz_name"),
            models.Index(fields=["business", "phone"], name="idx_customer_biz_phone"),
        ]

    def __str__(self):
        return f"{self.name} ({self.customer_code})"

    def save(self, *args, **kwargs):
        if not self.customer_code:
            self.customer_code = self._generate_code()
        super().save(*args, **kwargs)

    def _generate_code(self):
        """Generate next sequential customer code for this business."""
        last = (
            Customer.objects.filter(business_id=self.business_id)
            .order_by("-customer_code")
            .values_list("customer_code", flat=True)
            .first()
        )
        if last:
            try:
                num = int(last.split("-")[1]) + 1
            except (IndexError, ValueError):
                num = 1
        else:
            num = 1
        return f"CUST-{num:04d}"
