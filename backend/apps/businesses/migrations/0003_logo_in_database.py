"""Move the business logo from a file on disk into the database.

Add the new columns, copy every logo file that still exists on disk into them, then drop
the old file column. A logo whose file is already gone (e.g. lost on a redeploy) is left
empty — the owner uploads it again.
"""

from django.db import migrations, models

SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]


def _image_type(data):
    for magic, content_type in SIGNATURES:
        if data.startswith(magic):
            return content_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def copy_logo_files(apps, schema_editor):
    Business = apps.get_model("businesses", "Business")
    for business in Business.objects.exclude(logo="").exclude(logo__isnull=True):
        try:
            with business.logo.open("rb") as f:
                data = f.read()
        except (FileNotFoundError, OSError, ValueError):
            continue
        content_type = _image_type(data)
        if content_type and len(data) <= 2 * 1024 * 1024:
            Business.objects.filter(pk=business.pk).update(logo_data=data, logo_type=content_type)


class Migration(migrations.Migration):
    dependencies = [
        ("businesses", "0002_alter_business_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="logo_data",
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="business",
            name="logo_type",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.RunPython(copy_logo_files, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="business",
            name="logo",
        ),
    ]
