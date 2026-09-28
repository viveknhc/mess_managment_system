from django.urls import path

from apps.settings_app.views import BusinessSettingsView

urlpatterns = [
    path("settings/", BusinessSettingsView.as_view(), name="business-settings"),
]
