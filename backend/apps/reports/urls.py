"""Report URL routes — /api/v1/reports/*."""

from django.urls import path

from apps.reports.views import (
    CustomerReportView,
    MealReportView,
    PaymentReportView,
    RevenueReportView,
    SubscriptionReportView,
)

urlpatterns = [
    path("reports/customers/", CustomerReportView.as_view(), name="report-customers"),
    path("reports/subscriptions/", SubscriptionReportView.as_view(), name="report-subscriptions"),
    path("reports/revenue/", RevenueReportView.as_view(), name="report-revenue"),
    path("reports/meals/", MealReportView.as_view(), name="report-meals"),
    path("reports/payments/", PaymentReportView.as_view(), name="report-payments"),
]
