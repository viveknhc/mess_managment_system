"""Customer portal URL routes — /api/v1/portal/* (PT-01)."""

from django.urls import path

from apps.subscriptions.portal_views import (
    PortalDashboardView,
    PortalDeliveriesView,
    PortalPaymentsView,
    PortalProfileView,
    PortalSubscriptionActionsView,
    PortalSubscriptionsView,
)

actions = PortalSubscriptionActionsView.as_view()

urlpatterns = [
    path("portal/dashboard/", PortalDashboardView.as_view(), name="portal-dashboard"),
    path("portal/subscriptions/", PortalSubscriptionsView.as_view(), name="portal-subscriptions"),
    path(
        "portal/subscriptions/<uuid:sub_id>/skip/",
        actions,
        {"action": "skip"},
        name="portal-subscription-skip",
    ),
    path(
        "portal/subscriptions/<uuid:sub_id>/pause-request/",
        actions,
        {"action": "pause"},
        name="portal-subscription-pause",
    ),
    path(
        "portal/subscriptions/<uuid:sub_id>/renew/",
        actions,
        {"action": "renew"},
        name="portal-subscription-renew",
    ),
    path("portal/payments/", PortalPaymentsView.as_view(), name="portal-payments"),
    path("portal/deliveries/", PortalDeliveriesView.as_view(), name="portal-deliveries"),
    path("portal/profile/", PortalProfileView.as_view(), name="portal-profile"),
]
