from django.contrib import admin

from apps.settings_app.models import BusinessSettings


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ["business", "min_pause_days", "max_pause_days"]
