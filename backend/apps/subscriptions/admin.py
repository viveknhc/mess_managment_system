from django.contrib import admin

from apps.subscriptions.models import Subscription, SubscriptionItem


class SubscriptionItemInline(admin.TabularInline):
    model = SubscriptionItem
    fields = ["label", "price_per_meal", "position"]
    extra = 0


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    inlines = [SubscriptionItemInline]
    list_display = ["customer", "plan", "status", "start_date", "end_date", "total_amount", "paid_amount"]
    list_filter = ["status", "business"]
    search_fields = ["customer__name"]
    readonly_fields = ["created_at", "updated_at"]
