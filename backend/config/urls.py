"""Root URL configuration. All API routes live under /api/v1/ (arch. §8.1)."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    """Liveness probe (system_design.md §18). Deep DB/Redis checks land with those apps."""
    return JsonResponse({"status": "ok", "service": "mess-management"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.accounts.staff_urls")),
    path("api/v1/", include("apps.businesses.urls")),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.meals.urls")),
    path("api/v1/", include("apps.plans.urls")),
    path("api/v1/", include("apps.subscriptions.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/v1/", include("apps.deliveries.urls")),
    path("api/v1/", include("apps.dashboard.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.settings_app.urls")),
    path("api/v1/", include("apps.subscriptions.portal_urls")),
]

# Serve media files in development (production uses nginx/S3)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
