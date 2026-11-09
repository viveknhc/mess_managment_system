from django.contrib import admin

from apps.notifications.models import EmailLog, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "type", "is_read", "sent_at"]
    list_filter = ["type", "is_read"]
    search_fields = ["title", "message"]


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["kind", "ref_date", "recipients", "status", "business"]
    list_filter = ["kind", "status"]
    search_fields = ["recipients", "subject"]
