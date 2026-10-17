"""Nutrient scaling and recipe total domain functions.

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
All calculations use exact Decimals (D-05, AC-43).
Implements per-100g nutrient scaling, edible weight accounting, and recipe totals /
per-serving partitioning (spec §5.3, AC-45–47).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class NutrientProfile:
    """Nutrient amounts, either per 100g or as a scaled total."""

    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal = Decimal("0")

    def __add__(self, other: "NutrientProfile") -> "NutrientProfile":
        return NutrientProfile(
            calories=self.calories + other.calories,
            protein_g=self.protein_g + other.protein_g,
            carbs_g=self.carbs_g + other.carbs_g,
            fat_g=self.fat_g + other.fat_g,
            fiber_g=self.fiber_g + other.fiber_g,
        )

    def divide(self, divisor: Decimal) -> "NutrientProfile":
        if divisor <= Decimal("0"):
            raise ValueError("Divisor must be strictly positive")
        return NutrientProfile(
            calories=self.calories / divisor,
            protein_g=self.protein_g / divisor,
            carbs_g=self.carbs_g / divisor,
            fat_g=self.fat_g / divisor,
            fiber_g=self.fiber_g / divisor,
        )


@dataclass(frozen=True)
class RecipeIngredientInput:
    """Input for an ingredient in a recipe nutrient calculation."""

    food_nutrients: NutrientProfile
    quantity_g: Decimal
    edible_weight_g: Decimal | None = None


@dataclass(frozen=True)
class RecipeNutrientResult:
    """Calculated total and per-serving nutrient totals for a recipe."""

    total: NutrientProfile
    per_serving: NutrientProfile


def calculate_food_nutrients(
    weight_g: Decimal,
    per_100g: NutrientProfile,
) -> NutrientProfile:
    """Calculate nutrients for an edible weight of food in grams (spec §5.3, AC-45).

    Formula: nutrient = (edible weight in g / 100) × nutrient per 100 g.
    """
    factor = weight_g / Decimal("100")
    return NutrientProfile(
        calories=factor * per_100g.calories,
        protein_g=factor * per_100g.protein_g,
        carbs_g=factor * per_100g.carbs_g,
        fat_g=factor * per_100g.fat_g,
        fiber_g=factor * per_100g.fiber_g,
    )


def calculate_recipe_nutrients(
    ingredients: Iterable[RecipeIngredientInput],
    servings: Decimal,
) -> RecipeNutrientResult:
    """Calculate recipe total and per-serving nutrient amounts (spec §5.3, AC-46, AC-47).

    Rules:
    - If edible_weight_g is provided, it is used instead of purchased quantity_g (AC-46).
    - Per-serving nutrients are the sum over ingredients divided by recipe servings (AC-47).
    """
    if servings <= Decimal("0"):
        raise ValueError("Servings must be strictly positive")

    running_total = NutrientProfile(
        calories=Decimal("0"),
        protein_g=Decimal("0"),
        carbs_g=Decimal("0"),
        fat_g=Decimal("0"),
        fiber_g=Decimal("0"),
    )

    for ing in ingredients:
        # Use edible_weight_g if present, otherwise quantity_g (spec §5.3, AC-46)
        effective_weight = (
            ing.edible_weight_g if ing.edible_weight_g is not None else ing.quantity_g
        )
        ing_nutrients = calculate_food_nutrients(effective_weight, ing.food_nutrients)
        running_total = running_total + ing_nutrients

    per_serving = running_total.divide(servings)

    return RecipeNutrientResult(
        total=running_total,
        per_serving=per_serving,
    )
