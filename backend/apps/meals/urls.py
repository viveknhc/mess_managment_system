"""Meal URL routes — /api/v1/meals/*."""

from rest_framework.routers import DefaultRouter

from apps.meals.views import MealViewSet

router = DefaultRouter()
router.register("meals", MealViewSet, basename="meal")

urlpatterns = router.urls
