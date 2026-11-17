from django.contrib import admin

from apps.customization.models import BusinessFeature, BusinessPolicy


@admin.register(BusinessFeature)
class BusinessFeatureAdmin(admin.ModelAdmin):
    list_display = ["business", "key", "enabled", "updated_at"]
    list_filter = ["key", "enabled"]


@admin.register(BusinessPolicy)
class BusinessPolicyAdmin(admin.ModelAdmin):
    list_display = ["business", "point", "policy", "updated_at"]
    list_filter = ["point", "policy"]
