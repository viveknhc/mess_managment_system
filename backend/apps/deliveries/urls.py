"""Delivery URL routes — /api/v1/deliveries/*."""

from rest_framework.routers import DefaultRouter

from apps.deliveries.views import DeliveryViewSet

router = DefaultRouter()
router.register("deliveries", DeliveryViewSet, basename="delivery")

urlpatterns = router.urls
