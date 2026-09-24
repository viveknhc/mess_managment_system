"""Abstract base models (arch. §5, system_design.md §6)."""
import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """created_at / updated_at on everything."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """UUID primary key — non-enumerable (system_design.md D2).

    uuid4 today; switch default to stdlib uuid.uuid7 when Python 3.14 is baseline
    (time-sortable indexes).
    """

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)

    class Meta:
        abstract = True


class TenantScopedModel(UUIDModel, TimeStampedModel):
    """Every business-owned model inherits this — tenant isolation starts here."""

    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)

    class Meta:
        abstract = True
