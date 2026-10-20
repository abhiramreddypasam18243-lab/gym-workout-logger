"""Nutrition target estimation domain functions.

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
Implements the Mifflin–St Jeor formula, activity factors, goal adjustments,
macro defaults and safety energy floor checks (spec §5.4, S4, S5, AC-19–21).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

Sex = Literal["male", "female", "unspecified"]
ActivityLevel = Literal["sedentary", "light", "moderate", "very_active"]
Goal = Literal["maintain", "build_strength", "build_muscle"]

# Mifflin-St Jeor sex adjustment factor (s)
SEX_FACTORS: dict[Sex, Decimal] = {
    "male": Decimal("5"),
    "female": Decimal("-161"),
    "unspecified": Decimal("-78"),  # Midpoint between male and female
}

# Physical activity multiplier for TDEE
ACTIVITY_FACTORS: dict[ActivityLevel, Decimal] = {
    "sedentary": Decimal("1.2"),
    "light": Decimal("1.375"),
    "moderate": Decimal("1.55"),
    "very_active": Decimal("1.725"),
}

# Goal calorie multiplier (spec §5.4, D-11: no deficit/weight-loss goals supported)
GOAL_FACTORS: dict[Goal, Decimal] = {
    "maintain": Decimal("1.0"),
    "build_strength": Decimal("1.05"),  # +5%
    "build_muscle": Decimal("1.10"),  # +10% (initial placeholder for review, D-29)
}


class EstimateBelowFloorError(Exception):
    """Raised when an estimated target is below the safety energy floor."""

    pass


@dataclass(frozen=True)
class TargetEstimate:
    """Estimated nutrition targets with transparent calculation details and assumptions."""

    bmr: Decimal
    tdee: Decimal
    raw_calories: Decimal
    calories: int
    protein_g: int
    fat_g: int
    carbs_g: int
    is_below_floor: bool
    floor_threshold: Decimal
    assumptions: dict[str, Any]


def calculate_bmr(
    weight_kg: Decimal, height_cm: Decimal, age: int, sex: Sex = "unspecified"
) -> Decimal:
    """Calculate Basal Metabolic Rate using the Mifflin-St Jeor equation.

    BMR = 10 × weight_kg + 6.25 × height_cm − 5 × age + s
    s = +5 (male), -161 (female), -78 (unspecified midpoint)
    """
    s = SEX_FACTORS.get(sex, SEX_FACTORS["unspecified"])
    return (
        (Decimal("10") * weight_kg)
        + (Decimal("6.25") * height_cm)
        - (Decimal("5") * Decimal(age))
        + s
    )


def calculate_tdee(bmr: Decimal, activity_level: ActivityLevel) -> Decimal:
    """Calculate Total Daily Energy Expenditure (TDEE).

    TDEE = BMR × activity factor
    """
    factor = ACTIVITY_FACTORS[activity_level]
    return bmr * factor


def calculate_macro_defaults(
    calories: int,
    weight_kg: Decimal,
    protein_g_per_kg: Decimal = Decimal("1.6"),
    fat_pct: Decimal = Decimal("0.25"),
) -> dict[str, int]:
    """Calculate default macronutrient split from calories and body weight.

    - Protein: 1.6 g per kg of body weight (rounded to nearest 1 g)
    - Fat: 25% of calories divided by 9 kcal/g (rounded to nearest 1 g)
    - Carbohydrate: remaining calories divided by 4 kcal/g (rounded to nearest 1 g)
    """
    # Protein: 1.6 g per kg body weight
    raw_protein = weight_kg * protein_g_per_kg
    protein_g = int(raw_protein.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    protein_kcal = Decimal(protein_g) * Decimal("4")

    # Fat: 25% of calories (÷ 9 kcal per g)
    fat_kcal_target = Decimal(calories) * fat_pct
    raw_fat = fat_kcal_target / Decimal("9")
    fat_g = int(raw_fat.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    # Carbohydrate: remaining calories (÷ 4 kcal per g)
    # Spec §5.4 & AC-19: remaining = total - protein_kcal - fat_kcal_target
    remaining_kcal = Decimal(calories) - protein_kcal - fat_kcal_target
    raw_carbs = remaining_kcal / Decimal("4")
    carbs_g = int(raw_carbs.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return {
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carbs_g": carbs_g,
    }


def calculate_target_estimate(
    weight_kg: Decimal,
    height_cm: Decimal,
    age: int,
    sex: Sex = "unspecified",
    activity_level: ActivityLevel = "moderate",
    goal: Goal = "maintain",
    estimate_floor_kcal: Decimal = Decimal("1500"),
    protein_g_per_kg: Decimal = Decimal("1.6"),
    fat_pct: Decimal = Decimal("0.25"),
) -> TargetEstimate:
    """Generate transparent, optional target estimates with safety energy floor check."""
    bmr = calculate_bmr(weight_kg, height_cm, age, sex)
    tdee = calculate_tdee(bmr, activity_level)

    goal_multiplier = GOAL_FACTORS[goal]
    raw_calories = tdee * goal_multiplier

    # Round to nearest 10 calories (spec §5.4, AC-19)
    rounded_calories = int(
        (raw_calories / Decimal("10")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 10
    )

    # Safety energy floor check (spec S5, AC-21)
    is_below_floor = Decimal(rounded_calories) < estimate_floor_kcal

    macros = calculate_macro_defaults(
        calories=rounded_calories,
        weight_kg=weight_kg,
        protein_g_per_kg=protein_g_per_kg,
        fat_pct=fat_pct,
    )

    assumptions = {
        "formula": "Mifflin-St Jeor: 10*weight_kg + 6.25*height_cm - 5*age + s",
        "sex_factor_s": SEX_FACTORS.get(sex, SEX_FACTORS["unspecified"]),
        "activity_level": activity_level,
        "activity_factor": ACTIVITY_FACTORS[activity_level],
        "goal": goal,
        "goal_factor": goal_multiplier,
        "protein_g_per_kg": protein_g_per_kg,
        "fat_pct_calories": fat_pct,
    }

    return TargetEstimate(
        bmr=bmr,
        tdee=tdee,
        raw_calories=raw_calories,
        calories=rounded_calories,
        protein_g=macros["protein_g"],
        fat_g=macros["fat_g"],
        carbs_g=macros["carbs_g"],
        is_below_floor=is_below_floor,
        floor_threshold=estimate_floor_kcal,
        assumptions=assumptions,
    )
