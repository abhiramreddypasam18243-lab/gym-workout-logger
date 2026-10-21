"""Grocery list scaling, unit normalization, and aggregation domain functions.

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
All calculations use exact Decimals (D-05, AC-43).
Implements ingredient scaling, unit-family segregation (mass, volume, count;
no density conversions), and human-readable aggregation displays (spec §5.7, AC-77–79).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum


class UnitFamily(StrEnum):
    """Mutually incompatible unit families (spec §5.7, AC-78)."""

    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"


# Unit conversion factors to canonical base unit (g for mass, ml for volume, piece for count)
# Cooking volumes defined in spec §5.1, D-15: 1 tsp = 5 ml, 1 tbsp = 15 ml, 1 cup = 240 ml
UNIT_SPECS: dict[str, tuple[UnitFamily, Decimal, str]] = {
    # Mass (canonical unit: g)
    "g": (UnitFamily.MASS, Decimal("1"), "g"),
    "gram": (UnitFamily.MASS, Decimal("1"), "g"),
    "grams": (UnitFamily.MASS, Decimal("1"), "g"),
    "kg": (UnitFamily.MASS, Decimal("1000"), "g"),
    "kilogram": (UnitFamily.MASS, Decimal("1000"), "g"),
    # Volume (canonical unit: ml)
    "ml": (UnitFamily.VOLUME, Decimal("1"), "ml"),
    "l": (UnitFamily.VOLUME, Decimal("1000"), "ml"),
    "liter": (UnitFamily.VOLUME, Decimal("1000"), "ml"),
    "litre": (UnitFamily.VOLUME, Decimal("1000"), "ml"),
    "tsp": (UnitFamily.VOLUME, Decimal("5"), "ml"),
    "teaspoon": (UnitFamily.VOLUME, Decimal("5"), "ml"),
    "tbsp": (UnitFamily.VOLUME, Decimal("15"), "ml"),
    "tablespoon": (UnitFamily.VOLUME, Decimal("15"), "ml"),
    "cup": (UnitFamily.VOLUME, Decimal("240"), "ml"),
    "cups": (UnitFamily.VOLUME, Decimal("240"), "ml"),
    # Count (canonical unit: piece)
    "piece": (UnitFamily.COUNT, Decimal("1"), "piece"),
    "pieces": (UnitFamily.COUNT, Decimal("1"), "piece"),
    "item": (UnitFamily.COUNT, Decimal("1"), "piece"),
}


@dataclass(frozen=True)
class GroceryItemInput:
    """An ingredient occurrence from a planned meal."""

    name: str
    quantity: Decimal
    unit: str
    food_id: str | None = None
    category: str = "general"
    is_text_only: bool = False


@dataclass(frozen=True)
class AggregatedGroceryItem:
    """Consolidated grocery item for shopping checklist."""

    name: str
    total_quantity: Decimal
    canonical_unit: str
    unit_family: UnitFamily
    display_quantity: str
    food_id: str | None = None
    category: str = "general"
    is_text_only: bool = False


def scale_ingredient_quantity(
    quantity: Decimal,
    recipe_servings: Decimal,
    planned_servings: Decimal,
) -> Decimal:
    """Scale an ingredient quantity for planned servings (spec §5.7, AC-79).

    Formula: quantity × (planned servings / recipe servings)
    """
    if recipe_servings <= Decimal("0"):
        raise ValueError("Recipe servings must be strictly positive")
    return quantity * (planned_servings / recipe_servings)


def format_grocery_quantity(
    canonical_qty: Decimal,
    unit_family: UnitFamily,
) -> str:
    """Format canonical quantity into human-readable display string (spec §5.7, AC-77).

    Rules:
    - Mass: >= 1,000 g displays in kg (rounded to 1 decimal place half-up);
      < 1,000 g displays in g.
    - Volume: >= 1,000 ml displays in l (rounded to 1 decimal place half-up);
      < 1,000 ml displays in ml.
    - Count: displays in piece.
    """

    def _strip_zero(d: Decimal) -> str:
        # Format decimal cleanly (e.g. 750 or 1.2)
        s = f"{d}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s

    if unit_family == UnitFamily.MASS:
        if canonical_qty >= Decimal("1000"):
            kg_val = (canonical_qty / Decimal("1000")).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
            return f"{_strip_zero(kg_val)} kg"
        rounded_g = canonical_qty.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{_strip_zero(rounded_g)} g"

    elif unit_family == UnitFamily.VOLUME:
        if canonical_qty >= Decimal("1000"):
            l_val = (canonical_qty / Decimal("1000")).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
            return f"{_strip_zero(l_val)} l"
        rounded_ml = canonical_qty.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{_strip_zero(rounded_ml)} ml"

    else:
        rounded_count = canonical_qty.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{_strip_zero(rounded_count)} piece"


def aggregate_grocery_items(
    items: Iterable[GroceryItemInput],
) -> list[AggregatedGroceryItem]:
    """Aggregate ingredient quantities across planned meals.

    Rules (spec §5.7, AC-77, AC-78):
    - Quantities are summed ONLY within the same unit family (mass, volume, count).
    - Different families for the same food stay on separate lines (no density conversions).
    - Output is sorted deterministically by category, then item name, then unit family.
    """
    # Key: (identity_key, unit_family)
    grouped: dict[tuple[str, UnitFamily], list[tuple[GroceryItemInput, Decimal, str]]] = {}

    for item in items:
        unit_lower = item.unit.lower().strip()
        if unit_lower not in UNIT_SPECS:
            # Fallback for unrecognized unit: treat as isolated count
            family = UnitFamily.COUNT
            factor = Decimal("1")
            canonical_unit = unit_lower
        else:
            family, factor, canonical_unit = UNIT_SPECS[unit_lower]

        identity_key = item.food_id if item.food_id is not None else item.name.lower().strip()
        group_key = (identity_key, family)

        canonical_qty = item.quantity * factor
        if group_key not in grouped:
            grouped[group_key] = []
        grouped[group_key].append((item, canonical_qty, canonical_unit))

    aggregated: list[AggregatedGroceryItem] = []

    for (_ident, family), entries in grouped.items():
        first_item = entries[0][0]
        canonical_unit = entries[0][2]
        total_canonical = sum((e[1] for e in entries), Decimal("0"))
        any_text_only = any(e[0].is_text_only for e in entries)

        display = format_grocery_quantity(total_canonical, family)

        aggregated.append(
            AggregatedGroceryItem(
                food_id=first_item.food_id,
                name=first_item.name,
                total_quantity=total_canonical,
                canonical_unit=canonical_unit,
                unit_family=family,
                display_quantity=display,
                category=first_item.category,
                is_text_only=any_text_only,
            )
        )

    # Sort deterministically: category ascending, name ascending, unit_family ascending
    aggregated.sort(key=lambda x: (x.category, x.name.lower(), x.unit_family.value))
    return aggregated
