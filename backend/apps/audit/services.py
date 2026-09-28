"""Audit logging service (AU-02)."""

from apps.audit.models import AuditLog


class AuditService:
    @staticmethod
    def log(*, business_id, user=None, action, entity_type, entity_id, description=""):
        return AuditLog.objects.create(
            business_id=business_id,
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            description=description,
        )
