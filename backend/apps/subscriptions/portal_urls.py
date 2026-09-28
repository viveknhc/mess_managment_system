"""Customer portal URL routes — /api/v1/portal/*."""

from django.urls import path

from apps.subscriptions.portal_views import (
    PortalDashboardView,
    PortalDeliveriesView,
    PortalPaymentsView,
    PortalProfileView,
    PortalSubscriptionsView,
)

urlpatterns = [
    path("portal/dashboard/", PortalDashboardView.as_view(), name="portal-dashboard"),
    path("portal/subscriptions/", PortalSubscriptionsView.as_view(), name="portal-subscriptions"),
    path("portal/payments/", PortalPaymentsView.as_view(), name="portal-payments"),
    path("portal/deliveries/", PortalDeliveriesView.as_view(), name="portal-deliveries"),
    path("portal/profile/", PortalProfileView.as_view(), name="portal-profile"),
]
