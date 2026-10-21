from django.contrib import admin

from apps.platform.models import SaasPayment, SaasPlan, SaasSubscription


@admin.register(SaasPlan)
class SaasPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price_monthly", "max_customers", "max_staff", "is_active"]
    list_filter = ["is_active"]


@admin.register(SaasSubscription)
class SaasSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["business", "plan", "status", "trial_end_date", "current_period_end"]
    list_filter = ["status"]
    raw_id_fields = ["business", "plan"]


@admin.register(SaasPayment)
class SaasPaymentAdmin(admin.ModelAdmin):
    list_display = ["business", "amount", "status", "created_at"]
    list_filter = ["status"]
    raw_id_fields = ["business", "saas_subscription", "plan"]
