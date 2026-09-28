from django.contrib import admin

from apps.deliveries.models import Delivery, MealSkip, SubscriptionPause


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ["customer", "meal", "delivery_date", "status", "assigned_staff"]
    list_filter = ["status", "delivery_date", "business"]
    search_fields = ["customer__name"]


@admin.register(MealSkip)
class MealSkipAdmin(admin.ModelAdmin):
    list_display = ["customer", "skip_date", "reason"]


@admin.register(SubscriptionPause)
class SubscriptionPauseAdmin(admin.ModelAdmin):
    list_display = ["subscription", "start_date", "end_date", "reason"]
