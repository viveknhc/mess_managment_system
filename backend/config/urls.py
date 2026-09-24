"""Root URL configuration. All API routes live under /api/v1/ (arch. §8.1)."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView


def health(request):
    """Liveness probe (system_design.md §18). Deep DB/Redis checks land with those apps."""
    return JsonResponse({"status": "ok", "service": "mess-management"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/v1/", include("apps.businesses.urls")),
]
