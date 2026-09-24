"""User model (poc.md §7.2) — identity + role. Auth endpoints land in Module 1."""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from common.constants import ROLE_CHOICES


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # null only for future SUPER_ADMIN (platform staff, not tied to one business)
    business = models.ForeignKey(
        "businesses.Business", null=True, blank=True, on_delete=models.CASCADE, related_name="users"
    )
    name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="CUSTOMER")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name or self.username} ({self.role})"
