from django.apps import AppConfig


class CustomizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.customization"
    label = "customization"

    def ready(self):
        # Importing the policy modules registers them with their extension points.
        from apps.customization import policies  # noqa: F401
