"""Read the food quantity out of a customization label, for the kitchen's totals.

"Extra chicken 100g"  → ("Chicken", 100, "g")
"Add 2 chapati"       → ("Chapati", 2, "pcs")
"Extra curd 0.5 L"    → ("Curd", 500, "ml")
"No rice" / "Less spicy" / "Extra chicken" (no amount) → None — shown as a request, not food.

Amounts are normalised to g / ml / pcs so the same food adds up (100g ×5 = 500 g).
"""

import re
from decimal import Decimal, InvalidOperation

_UNITS = {
    "g": ("g", 1), "gm": ("g", 1), "gms": ("g", 1), "gram": ("g", 1), "grams": ("g", 1),
    "kg": ("g", 1000), "kgs": ("g", 1000),
    "ml": ("ml", 1), "l": ("ml", 1000), "ltr": ("ml", 1000), "litre": ("ml", 1000),
    "liter": ("ml", 1000), "litres": ("ml", 1000), "liters": ("ml", 1000),
    "pc": ("pcs", 1), "pcs": ("pcs", 1), "piece": ("pcs", 1), "pieces": ("pcs", 1), "nos": ("pcs", 1),
}  # fmt: skip
_AMOUNT = re.compile(
    r"(?<![\w.])(?:x\s*)?(\d+(?:\.\d+)?)\s*("
    + "|".join(sorted(_UNITS, key=len, reverse=True))
    + r")?(?:\s*x)?(?!\w)",
    re.IGNORECASE,
)
_NOT_FOOD = re.compile(r"^\s*(no|less|without|skip|only)\b", re.IGNORECASE)
_FILLER = re.compile(r"\b(extra|add|additional|more|plus)\b|\+", re.IGNORECASE)


def parse_extra(label):
    """``(food, quantity: Decimal, unit)`` for a label with an amount, else None."""
    if _NOT_FOOD.match(label):
        return None
    matches = list(_AMOUNT.finditer(label))
    if len(matches) != 1:  # no amount, or ambiguous ("2 eggs 100g")
        return None
    m = matches[0]
    try:
        qty = Decimal(m.group(1))
    except InvalidOperation:
        return None
    unit, factor = _UNITS[m.group(2).lower()] if m.group(2) else ("pcs", 1)
    food = _FILLER.sub(" ", label[: m.start()] + " " + label[m.end() :])
    food = " ".join(food.split()).strip(" -,:")
    if not food or qty <= 0:
        return None
    return food[0].upper() + food[1:].lower(), qty * factor, unit
