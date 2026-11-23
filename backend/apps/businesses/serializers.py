"""Business serializers (Module 2)."""

import base64

from rest_framework import serializers

from apps.businesses.models import Business

MAX_LOGO_BYTES = 1024 * 1024  # 1 MB — sent inline with the business profile

_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]


def image_type(data):
    """Content type of a PNG/JPEG/GIF/WebP image from its first bytes, else None.
    Checked on the bytes, not the file name or the browser's claim."""
    for magic, content_type in _SIGNATURES:
        if data.startswith(magic):
            return content_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def logo_data_url(business):
    """The logo as a data: URL, so it shows wherever the app is opened (no /media/ needed)."""
    if not business.logo_data or not business.logo_type:
        return None
    return f"data:{business.logo_type};base64,{base64.b64encode(bytes(business.logo_data)).decode()}"


class BusinessSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "address",
            "logo",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def get_logo(self, obj):
        return logo_data_url(obj)


class BusinessUpdateSerializer(serializers.ModelSerializer):
    """Owner-only update — cannot change status or id.

    ``logo``: an image file (PNG, JPEG, WebP or GIF, max 1 MB) to replace the logo,
    or null / "" to remove it.
    """

    logo = serializers.FileField(write_only=True, required=False, allow_null=True, allow_empty_file=False)

    class Meta:
        model = Business
        fields = ["name", "phone", "email", "address", "logo"]

    def to_internal_value(self, data):
        # A multipart/form "logo=" (empty string) means "remove the logo".
        if hasattr(data, "get") and data.get("logo") == "":
            data = data.copy()
            data["logo"] = None
        return super().to_internal_value(data)

    def validate_logo(self, upload):
        if upload is None:
            return None
        if upload.size > MAX_LOGO_BYTES:
            raise serializers.ValidationError("The logo must be 1 MB or smaller.")
        data = upload.read()
        content_type = image_type(data)
        if content_type is None:
            raise serializers.ValidationError("Upload a PNG, JPEG, WebP or GIF image.")
        return {"data": data, "type": content_type}

    def update(self, instance, validated_data):
        if "logo" in validated_data:
            logo = validated_data.pop("logo")
            instance.logo_data = logo["data"] if logo else None
            instance.logo_type = logo["type"] if logo else ""
        return super().update(instance, validated_data)
