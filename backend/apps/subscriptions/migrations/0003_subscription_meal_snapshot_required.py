"""Make the plan snapshot required once 0002 has filled it for existing rows.

Separate migration so the data copy and the NOT NULL change run in different
transactions (Postgres refuses ALTER TABLE with pending deferred FK checks).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meals", "0001_initial"),
        ("subscriptions", "0002_subscription_meal_snapshot"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscription",
            name="meal",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="+", to="meals.meal"
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="total_meals",
            field=models.PositiveIntegerField(),
        ),
    ]
