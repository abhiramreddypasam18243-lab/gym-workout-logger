"""Planned vs Logged nutrition comparison domain functions (spec §5.8, AC-83, AC-84).

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
All calculations use exact Decimals (D-05).
Strictly adheres to Rule S6 neutral language rules (no cheat, bad, failed, guilt).
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PlannedVsLoggedComparison:
    """Mathematical evaluation of a day's planned vs logged intake."""

    calories_diff: Decimal
    calories_diff_pct: Decimal
    protein_diff_g: Decimal
    protein_diff_pct: Decimal
    is_within_range: bool
    status_label: str


def compare_planned_vs_logged(
    planned_calories: Decimal,
    planned_protein: Decimal,
    logged_calories: Decimal,
    logged_protein: Decimal,
) -> PlannedVsLoggedComparison:
    """Compare logged intake against planned intake for a single day (spec §5.8, AC-83).

    Rules:
    - Difference = logged − planned
    - Difference % = (difference / planned) × 100
    - "Within range":
      - Calories difference % is between -10.0% and +10.0% inclusive (|diff_pct| <= 10.0%)
      - Protein is at least 90.0% of planned (logged_protein >= 0.90 * planned_protein)
    - Labels are strictly neutral:
      - "Within target range"
      - "Below planned calorie range"
      - "Above planned calorie range"
      - "Protein below target"

    Example from spec AC-83:
      Planned: 2900 kcal, 125 g protein
      Logged:  2610 kcal, 140 g protein
      Difference: -290 kcal (-10.0%) and +15 g (+12.0%)
      Result: is_within_range = True (the 10% limit is inclusive)
    """
    if planned_calories <= Decimal("0"):
        raise ValueError("Planned calories must be strictly positive")
    if planned_protein <= Decimal("0"):
        raise ValueError("Planned protein must be strictly positive")

    cal_diff = logged_calories - planned_calories
    cal_diff_pct = (cal_diff / planned_calories) * Decimal("100")

    prot_diff = logged_protein - planned_protein
    prot_diff_pct = (prot_diff / planned_protein) * Decimal("100")

    # Within range check (AC-83: 10% limit is inclusive)
    cal_within = abs(cal_diff / planned_calories) <= Decimal("0.10000000001")
    prot_within = logged_protein >= (Decimal("0.90") * planned_protein)

    is_within = cal_within and prot_within

    if is_within:
        label = "Within target range"
    elif not cal_within and cal_diff < Decimal("0"):
        label = "Below planned calorie range"
    elif not cal_within and cal_diff > Decimal("0"):
        label = "Above planned calorie range"
    else:
        label = "Protein below target"

    return PlannedVsLoggedComparison(
        calories_diff=cal_diff,
        calories_diff_pct=cal_diff_pct,
        protein_diff_g=prot_diff,
        protein_diff_pct=prot_diff_pct,
        is_within_range=is_within,
        status_label=label,
    )
