"""Platform billing URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.platform.views import (
    BillingView,
    CheckoutView,
    PlatformBusinessViewSet,
    PlatformPaymentListView,
    PlatformPlanViewSet,
    PlatformStatsView,
    PublicPlansView,
    RazorpayWebhookView,
    SignupView,
)

router = DefaultRouter()
router.register("platform/businesses", PlatformBusinessViewSet, basename="platform-businesses")
router.register("platform/plans", PlatformPlanViewSet, basename="platform-plans")

urlpatterns = [
    # Public
    path("signup/", SignupView.as_view(), name="signup"),
    path("pricing/", PublicPlansView.as_view(), name="public-plans"),
    path("webhooks/razorpay/", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
    # Business owner billing
    path("billing/", BillingView.as_view(), name="billing"),
    path("billing/checkout/", CheckoutView.as_view(), name="billing-checkout"),
    # SUPER_ADMIN platform management
    path("platform/payments/", PlatformPaymentListView.as_view(), name="platform-payments"),
    path("platform/stats/", PlatformStatsView.as_view(), name="platform-stats"),
    # Router-based (businesses CRUD, plans CRUD)
    path("", include(router.urls)),
]
