"""Delivery URL routes — /api/v1/deliveries/*."""

from rest_framework.routers import DefaultRouter

from apps.deliveries.views import DeliveryRouteViewSet, DeliveryViewSet

router = DefaultRouter()
router.register("deliveries", DeliveryViewSet, basename="delivery")
router.register("delivery-routes", DeliveryRouteViewSet, basename="delivery-route")

urlpatterns = router.urls
