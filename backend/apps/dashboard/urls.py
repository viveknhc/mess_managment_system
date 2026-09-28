"""Dashboard URL routes — /api/v1/dashboard/."""

from django.urls import path

from apps.dashboard.views import DashboardView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
