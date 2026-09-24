"""Business profile API (Module 2 flesh-out; minimal self-service viewset for Module 0)."""

from rest_framework import serializers, viewsets

from apps.businesses.models import Business


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ["id", "name", "phone", "email", "address", "logo", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]


class BusinessViewSet(viewsets.ModelViewSet):
    """Users see and manage only their own business."""

    serializer_class = BusinessSerializer

    def get_queryset(self):
        return Business.objects.filter(id=self.request.user.business_id)
