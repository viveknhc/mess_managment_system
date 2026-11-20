"""Recount remaining_meals for existing subscriptions — it was set at creation and never
updated. Same rule as SubscriptionService.refresh_remaining_meals."""

from django.db import migrations

ENDED = ("CANCELLED", "EXPIRED")
WENT_OUT = ("OUT_FOR_DELIVERY", "DELIVERED", "NOT_DELIVERED")


def recount(apps, schema_editor):
    Subscription = apps.get_model("subscriptions", "Subscription")
    Delivery = apps.get_model("deliveries", "Delivery")
    for sub in Subscription.objects.iterator():
        if sub.status in ENDED:
            remaining = 0
        else:
            rows = Delivery.objects.filter(subscription_id=sub.id)
            went_out = rows.filter(status__in=WENT_OUT).count()
            skipped = rows.filter(status="SKIPPED")
            extended = skipped.filter(skip_record__adjustment="EXTEND").distinct().count()
            remaining = max(sub.total_meals - went_out - (skipped.count() - extended), 0)
        if remaining != sub.remaining_meals:
            Subscription.objects.filter(pk=sub.pk).update(remaining_meals=remaining)


class Migration(migrations.Migration):
    dependencies = [
        ("deliveries", "0003_mealskip_adjustment"),
        ("subscriptions", "0003_subscription_meal_snapshot_required"),
    ]

    operations = [migrations.RunPython(recount, migrations.RunPython.noop)]
