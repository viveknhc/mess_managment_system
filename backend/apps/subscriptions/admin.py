from django.contrib import admin

from apps.subscriptions.models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["customer", "plan", "status", "start_date", "end_date", "total_amount", "paid_amount"]
    list_filter = ["status", "business"]
    search_fields = ["customer__name"]
    readonly_fields = ["created_at", "updated_at"]
