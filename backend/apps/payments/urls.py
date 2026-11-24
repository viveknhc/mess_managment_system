"""Payment URL routes — /api/v1/payments/*."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.payments.views import CustomerPaymentWebhookView, PaymentViewSet, UpiClaimViewSet

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")
router.register("upi-claims", UpiClaimViewSet, basename="upi-claim")

urlpatterns = [
    path(
        "webhooks/razorpay/mess/<uuid:business_id>/",
        CustomerPaymentWebhookView.as_view(),
        name="customer-payment-webhook",
    ),
    *router.urls,
]
