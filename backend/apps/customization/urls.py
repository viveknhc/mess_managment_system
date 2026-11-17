from django.urls import path

from apps.customization.views import BusinessCustomizationView, CustomizationCatalogView

urlpatterns = [
    path("platform/customization/catalog/", CustomizationCatalogView.as_view(), name="customization-catalog"),
    path(
        "platform/businesses/<uuid:pk>/customization/",
        BusinessCustomizationView.as_view(),
        name="business-customization",
    ),
]
