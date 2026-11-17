"""Per-business customization rows, managed by SUPER_ADMIN. The catalog lives in registry.py."""

from django.db import models

from common.models import TenantScopedModel


class BusinessFeature(TenantScopedModel):
    """Override of one feature for one business — wins over the SaaS plan's list."""

    key = models.CharField(max_length=50)
    enabled = models.BooleanField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "key"], name="uniq_business_feature")]

    def __str__(self):
        return f"{self.business_id} {self.key}={'on' if self.enabled else 'off'}"


class BusinessPolicy(TenantScopedModel):
    """The policy a business uses at one extension point. No row = the point's default."""

    point = models.CharField(max_length=50)
    policy = models.CharField(max_length=50)
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "business policies"
        constraints = [models.UniqueConstraint(fields=["business", "point"], name="uniq_business_policy")]

    def __str__(self):
        return f"{self.business_id} {self.point}={self.policy}"
