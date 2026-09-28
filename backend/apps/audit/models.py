"""AuditLog model (AU-01). Immutable log of state-changing actions."""

import uuid

from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Immutable audit trail entry. Not tenant-scoped (uses raw FK for flexibility)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE, related_name="audit_logs")
    user = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=50)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} — {self.entity_type}:{self.entity_id}"
