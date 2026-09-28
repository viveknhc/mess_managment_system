from django.contrib import admin

from apps.settings_app.models import BusinessSettings


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ["business", "skip_rule", "max_skip_days", "max_pause_days"]
