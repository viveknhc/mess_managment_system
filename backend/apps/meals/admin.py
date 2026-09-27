from django.contrib import admin

from apps.meals.models import Meal


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "is_active", "business"]
    list_filter = ["is_active", "business"]
    search_fields = ["name"]
