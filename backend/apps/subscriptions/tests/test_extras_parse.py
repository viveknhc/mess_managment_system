"""Reading food amounts out of customization labels (kitchen extra-food totals)."""

from decimal import Decimal

import pytest

from apps.subscriptions.extras import parse_extra


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Extra chicken 100g", ("Chicken", Decimal("100"), "g")),
        ("extra  CHICKEN 100 g", ("Chicken", Decimal("100"), "g")),
        ("Extra rice 1kg", ("Rice", Decimal("1000"), "g")),
        ("Paneer 75 gms", ("Paneer", Decimal("75"), "g")),
        ("Extra curd 0.5 L", ("Curd", Decimal("500"), "ml")),
        ("Extra curd 100ml", ("Curd", Decimal("100"), "ml")),
        ("Add 2 chapati", ("Chapati", Decimal("2"), "pcs")),
        ("Chapati x2", ("Chapati", Decimal("2"), "pcs")),
        ("+1 egg", ("Egg", Decimal("1"), "pcs")),
        ("Fish fry 1 pc", ("Fish fry", Decimal("1"), "pcs")),
        ("Boiled eggs 2 nos", ("Boiled eggs", Decimal("2"), "pcs")),
    ],
)
def test_reads_food_amount(label, expected):
    assert parse_extra(label) == expected


@pytest.mark.parametrize(
    "label",
    [
        "No rice",
        "Less spicy",
        "Without onion",
        "Extra chicken",
        "No rice 100g",
        "2 eggs 100g",
        "100g",
        "Extra 0g chicken",
    ],
)
def test_not_food_to_cook(label):
    assert parse_extra(label) is None


def test_seed_customizations_refuses_in_production(settings, db):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    settings.DEBUG = False
    with pytest.raises(CommandError, match="Demo data only"):
        call_command("seed_customizations")
