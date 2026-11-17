"""BusinessSettings.skip_rule (owner-editable, never applied) → BusinessPolicy ``skip`` (SUPER_ADMIN).

EXTEND carries over. CREDIT had no implementation and isn't a registered policy,
so it becomes the default (NONE) — same behaviour as before.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    BusinessSettings = apps.get_model("settings_app", "BusinessSettings")
    BusinessPolicy = apps.get_model("customization", "BusinessPolicy")
    for business_id in BusinessSettings.objects.filter(skip_rule="EXTEND").values_list("business_id", flat=True):
        BusinessPolicy.objects.get_or_create(
            business_id=business_id, point="skip", defaults={"policy": "EXTEND", "params": {}}
        )


def backwards(apps, schema_editor):
    BusinessSettings = apps.get_model("settings_app", "BusinessSettings")
    BusinessPolicy = apps.get_model("customization", "BusinessPolicy")
    ids = BusinessPolicy.objects.filter(point="skip", policy="EXTEND").values_list("business_id", flat=True)
    BusinessSettings.objects.filter(business_id__in=list(ids)).update(skip_rule="EXTEND")


class Migration(migrations.Migration):
    dependencies = [
        ("customization", "0001_initial"),
        ("settings_app", "0002_businesssettings_online_payments_enabled_and_more"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
