from django.contrib import admin

from apps.businesses.models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "status", "created_at")
    search_fields = ("name", "phone")
