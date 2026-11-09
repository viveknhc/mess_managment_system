"""Platform billing URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.platform.views import (
    BillingCancelView,
    BillingView,
    PlatformBusinessViewSet,
    PlatformPaymentListView,
    PlatformPlanViewSet,
    PlatformStatsView,
    PublicPlansView,
    RazorpayWebhookView,
)

router = DefaultRouter()
router.register("platform/businesses", PlatformBusinessViewSet, basename="platform-businesses")
router.register("platform/plans", PlatformPlanViewSet, basename="platform-plans")

urlpatterns = [
    # Public
    path("pricing/", PublicPlansView.as_view(), name="public-plans"),
    path("webhooks/razorpay/", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
    # Business owner billing
    path("billing/", BillingView.as_view(), name="billing"),
    path("billing/cancel/", BillingCancelView.as_view(), name="billing-cancel"),
    # SUPER_ADMIN platform management
    path("platform/payments/", PlatformPaymentListView.as_view(), name="platform-payments"),
    path("platform/stats/", PlatformStatsView.as_view(), name="platform-stats"),
    # Router-based (businesses CRUD, plans CRUD)
    path("", include(router.urls)),
]
