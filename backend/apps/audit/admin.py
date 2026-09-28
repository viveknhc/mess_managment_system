from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "entity_id", "user", "created_at"]
    list_filter = ["action", "entity_type", "business"]
    search_fields = ["description", "entity_id"]
    readonly_fields = [
        "id",
        "business",
        "user",
        "action",
        "entity_type",
        "entity_id",
        "description",
        "created_at",
    ]
    date_hierarchy = "created_at"
