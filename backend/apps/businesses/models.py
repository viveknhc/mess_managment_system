"""Business = the tenant (poc.md §7.1). One row per mess business."""

import uuid

from django.db import models

from common.constants import Status
from common.models import TimeStampedModel, UUIDModel


class Business(UUIDModel, TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    logo = models.FileField(upload_to="business_logos/", null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[(Status.ACTIVE, "Active"), (Status.INACTIVE, "Inactive"), (Status.SUSPENDED, "Suspended")],
        default=Status.ACTIVE,
    )

    def __str__(self):
        return self.name
