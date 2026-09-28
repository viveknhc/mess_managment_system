"""Payment URL routes — /api/v1/payments/*."""

from rest_framework.routers import DefaultRouter

from apps.payments.views import PaymentViewSet

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = router.urls
