from django.contrib import admin

from apps.payments.models import Payment, UpiPaymentClaim


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["customer", "amount", "method", "status", "payment_date", "business"]
    list_filter = ["status", "method", "business"]
    search_fields = ["customer__name", "transaction_reference"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(UpiPaymentClaim)
class UpiPaymentClaimAdmin(admin.ModelAdmin):
    list_display = ["customer", "amount", "utr", "status", "created_at", "business"]
    list_filter = ["status", "business"]
    search_fields = ["customer__name", "utr"]
    readonly_fields = ["created_at", "updated_at", "reviewed_at"]
