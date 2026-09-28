from django.contrib import admin

from apps.payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["customer", "amount", "method", "status", "payment_date", "business"]
    list_filter = ["status", "method", "business"]
    search_fields = ["customer__name", "transaction_reference"]
    readonly_fields = ["created_at", "updated_at"]
