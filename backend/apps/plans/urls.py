"""Plan URL routes — /api/v1/plans/*."""

from rest_framework.routers import DefaultRouter

from apps.plans.views import PlanViewSet

router = DefaultRouter()
router.register("plans", PlanViewSet, basename="plan")

urlpatterns = router.urls
