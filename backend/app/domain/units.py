"""Unit conversion domain functions.

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
All arithmetic uses Decimal for exact representation (D-05, AC-16, AC-43).
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

# Exactly defined conversion factor (spec §5.1, AC-16)
# 1 lb = 0.45359237 kg
LB_IN_KG = Decimal("0.45359237")

# Volume unit factors in millilitres (spec §5.1, D-15)
VOLUME_FACTORS_ML = {
    "ml": Decimal("1"),
    "tsp": Decimal("5"),
    "tbsp": Decimal("15"),
    "cup": Decimal("240"),
    "l": Decimal("1000"),
}


def lb_to_kg(lb: Decimal) -> Decimal:
    """Convert pounds (lb) to kilograms (kg) exactly."""
    return lb * LB_IN_KG


def kg_to_lb(kg: Decimal) -> Decimal:
    """Convert kilograms (kg) to pounds (lb)."""
    return kg / LB_IN_KG


def tsp_to_ml(tsp: Decimal) -> Decimal:
    """Convert teaspoons (tsp) to millilitres (ml)."""
    return tsp * VOLUME_FACTORS_ML["tsp"]


def tbsp_to_ml(tbsp: Decimal) -> Decimal:
    """Convert tablespoons (tbsp) to millilitres (ml)."""
    return tbsp * VOLUME_FACTORS_ML["tbsp"]


def cup_to_ml(cup: Decimal) -> Decimal:
    """Convert cups to millilitres (ml)."""
    return cup * VOLUME_FACTORS_ML["cup"]


def format_weight(weight: Decimal, unit: Literal["kg", "lb"] = "kg") -> str:
    """Format weight for display, rounded half-up to 1 decimal place (spec §5.1)."""
    rounded = weight.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{rounded} {unit}"
