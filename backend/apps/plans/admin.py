from django.contrib import admin

from apps.plans.models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "meal", "duration_days", "total_meals", "price", "is_active", "business"]
    list_filter = ["is_active", "business", "meal"]
    search_fields = ["name"]
