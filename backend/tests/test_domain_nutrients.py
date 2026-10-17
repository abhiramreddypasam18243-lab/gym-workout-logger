"""Tests for nutrient calculation domain functions.

Acceptance criteria:
AC-45 (FR-09): 150 g of a food with 20 g protein per 100 g gives exactly 30 g protein.
AC-46 (5.3): An ingredient of 200 g with edible_weight_g 150 uses 150 g in the calculation.
AC-47 (5.3): Fixture recipe:
    F1 (per 100 g): 150 kcal, 25 g protein, 0 g carbohydrate, 5 g fat.
    F2 (per 100 g): 350 kcal, 8 g protein, 75 g carbohydrate, 1 g fat.
    Recipe with 200 g F1 and 100 g F2 for 2 servings totals:
    650 kcal, 58 g protein, 75 g carbohydrate, 11 g fat.
    Per serving: 325 kcal, 29 g protein, 37.5 g carbohydrate, 5.5 g fat.
"""

from decimal import Decimal

from app.domain.nutrients import (
    NutrientProfile,
    RecipeIngredientInput,
    calculate_food_nutrients,
    calculate_recipe_nutrients,
)


def test_ac_45_nutrient_scaling_exact():
    # 150 g of food with 20 g protein per 100 g gives exactly 30 g protein
    nutrients_per_100g = NutrientProfile(
        calories=Decimal("100"),
        protein_g=Decimal("20"),
        carbs_g=Decimal("0"),
        fat_g=Decimal("0"),
    )
    result = calculate_food_nutrients(
        weight_g=Decimal("150"),
        per_100g=nutrients_per_100g,
    )
    assert result.protein_g == Decimal("30")


def test_ac_46_edible_weight_preference():
    # Ingredient of 200 g with edible_weight_g = 150 uses 150 g in calculation
    f = NutrientProfile(
        calories=Decimal("100"),
        protein_g=Decimal("20"),
        carbs_g=Decimal("0"),
        fat_g=Decimal("0"),
    )
    ing = RecipeIngredientInput(
        food_nutrients=f,
        quantity_g=Decimal("200"),
        edible_weight_g=Decimal("150"),
    )
    res = calculate_recipe_nutrients(ingredients=[ing], servings=Decimal("1"))
    # 150 g used -> protein should be 30 g, NOT 40 g (which 200 g would yield)
    assert res.total.protein_g == Decimal("30")


def test_ac_47_fixture_recipe():
    # Fixture foods (test fixtures only, per 100 g, AC-47 / DL4)
    f1 = NutrientProfile(
        calories=Decimal("150"),
        protein_g=Decimal("25"),
        carbs_g=Decimal("0"),
        fat_g=Decimal("5"),
    )
    f2 = NutrientProfile(
        calories=Decimal("350"),
        protein_g=Decimal("8"),
        carbs_g=Decimal("75"),
        fat_g=Decimal("1"),
    )

    # Recipe: 200 g F1 and 100 g F2, 2 servings
    ing1 = RecipeIngredientInput(food_nutrients=f1, quantity_g=Decimal("200"))
    ing2 = RecipeIngredientInput(food_nutrients=f2, quantity_g=Decimal("100"))

    result = calculate_recipe_nutrients(
        ingredients=[ing1, ing2],
        servings=Decimal("2"),
    )

    # Totals: 650 kcal, 58 g protein, 75 g carbohydrate, 11 g fat
    assert result.total.calories == Decimal("650")
    assert result.total.protein_g == Decimal("58")
    assert result.total.carbs_g == Decimal("75")
    assert result.total.fat_g == Decimal("11")

    # Per serving: 325 kcal, 29 g protein, 37.5 g carbohydrate, 5.5 g fat
    assert result.per_serving.calories == Decimal("325")
    assert result.per_serving.protein_g == Decimal("29")
    assert result.per_serving.carbs_g == Decimal("37.5")
    assert result.per_serving.fat_g == Decimal("5.5")
