"""Staff management URL routes — /api/v1/staff/*."""

from rest_framework.routers import DefaultRouter

from apps.accounts.views import StaffViewSet

router = DefaultRouter()
router.register("staff", StaffViewSet, basename="staff")

urlpatterns = router.urls
