from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["customer_code", "name", "phone", "status", "business"]
    list_filter = ["status", "business"]
    search_fields = ["name", "phone", "customer_code"]
    readonly_fields = ["customer_code", "created_at", "updated_at"]
