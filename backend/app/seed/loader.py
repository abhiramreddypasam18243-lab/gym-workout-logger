"""Catalogue seed loader and data integrity validators (spec §4, DL1–4, S9, FR-18, AC-48–52)."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.allergens import EU_ALLERGENS
from app.domain.nutrients import check_atwater_consistency
from app.models.nutrition import (
    Food,
    FoodAllergen,
    FoodNutrient,
    Recipe,
    RecipeDietTag,
    RecipeIngredient,
    RecipeMealType,
)
from app.models.workout import Exercise

DATA_DIR = Path(__file__).resolve().parent / "data"


def validate_food_provenance(food: dict[str, Any]) -> None:
    """Validate food provenance requirements (spec DL1, AC-49).

    Must have data_source, serving_description (serving basis), state, and verified_at.
    """
    name = food.get("name", "Unknown")
    required_fields = ["data_source", "serving_description", "state", "verified_at"]
    missing = [f for f in required_fields if not food.get(f)]
    if missing:
        raise ValueError(
            f"Food '{name}' is missing required provenance fields: {', '.join(missing)}"
        )


def validate_food_allergens(food: dict[str, Any]) -> None:
    """Every allergen code must be one of the 14 EU codes the planner filters on (S9, D-31)."""
    unknown = [a for a in food.get("allergens", []) if a.strip().lower() not in EU_ALLERGENS]
    if unknown:
        raise ValueError(f"Food '{food.get('name')}' has unknown allergen codes: {', '.join(unknown)}")


def validate_food_atwater(food: dict[str, Any]) -> None:
    """Validate 4-4-9 Atwater energy balance for non-exception foods (spec §4, DL1, AC-50).

    |kcal - (4*P + 4*C + 9*F)| <= max(20, 0.15 * kcal).
    """
    if food.get("approximate", False):
        return

    nutrients = food.get("nutrients", {})
    energy_kcal = Decimal(str(nutrients.get("energy_kcal", 0)))
    protein_g = Decimal(str(nutrients.get("protein_g", 0)))
    carbs_g = Decimal(str(nutrients.get("carbs_g", 0)))
    fat_g = Decimal(str(nutrients.get("fat_g", 0)))

    if not check_atwater_consistency(energy_kcal, protein_g, carbs_g, fat_g):
        raise ValueError(
            f"Food '{food.get('name')}' violates Atwater 4-4-9 energy balance: "
            f"claimed {energy_kcal} kcal against macros {protein_g}P / {carbs_g}C / {fat_g}F"
        )


def compute_recipe_allergens(
    ingredients: list[dict[str, Any]],
    foods_by_name: dict[str, Food],
) -> tuple[set[str], bool]:
    """Compute recipe allergens as the strict union of ingredient food allergens (AC-52).

    If any ingredient is text-only (no food_name) or has unverified allergens,
    flag incomplete allergen data as True.
    """
    allergen_union: set[str] = set()
    has_incomplete_data = False

    for ing in ingredients:
        food_name = ing.get("food_name")
        if not food_name or food_name not in foods_by_name:
            has_incomplete_data = True
            continue

        food_obj = foods_by_name[food_name]
        if not food_obj.allergens_verified:
            has_incomplete_data = True

        for fa in food_obj.allergens:
            allergen_union.add(fa.allergen_code)

    return allergen_union, has_incomplete_data


async def seed_exercises(session: AsyncSession) -> int:
    """Load curated exercises into database idempotently (AC-51)."""
    with open(DATA_DIR / "exercises.json", encoding="utf-8") as f:
        exercises_data = json.load(f)

    # Fetch existing exercise names (case-insensitive)
    existing_result = await session.execute(
        select(Exercise.name).where(Exercise.owner_user_id.is_(None))
    )
    existing_names = {row[0].strip().lower() for row in existing_result.all()}

    inserted_count = 0
    for ex in exercises_data:
        name_clean = ex["name"].strip()
        if name_clean.lower() in existing_names:
            continue

        exercise = Exercise(
            name=name_clean,
            primary_muscle=ex["primary_muscle"],
            equipment=ex["equipment"],
            movement_pattern=ex.get("movement_pattern", ""),
            instructions=ex.get("instructions"),
            is_custom=False,
            owner_user_id=None,
        )
        session.add(exercise)
        existing_names.add(name_clean.lower())
        inserted_count += 1

    return inserted_count


async def seed_foods(session: AsyncSession) -> tuple[int, dict[str, Food]]:
    """Validate and load foods into database idempotently (AC-49, AC-50, AC-51)."""
    with open(DATA_DIR / "foods.json", encoding="utf-8") as f:
        foods_data = json.load(f)

    # First pass: validate all provenance and Atwater constraints
    for f_data in foods_data:
        validate_food_provenance(f_data)
        validate_food_atwater(f_data)
        validate_food_allergens(f_data)

    existing_result = await session.execute(select(Food))
    existing_foods = {f.name.strip().lower(): f for f in existing_result.scalars().all()}

    inserted_count = 0
    all_foods_by_name: dict[str, Food] = dict(existing_foods)

    for f_data in foods_data:
        name_clean = f_data["name"].strip()
        name_lower = name_clean.lower()
        if name_lower in existing_foods:
            continue

        verified_at_val = None
        if f_data.get("verified_at"):
            verified_at_val = date.fromisoformat(f_data["verified_at"])

        food = Food(
            name=name_clean,
            food_category=f_data["food_category"],
            cuisine_code=f_data.get("cuisine_code"),
            serving_description=f_data["serving_description"],
            default_serving_g=Decimal(str(f_data["default_serving_g"]))
            if f_data.get("default_serving_g")
            else None,
            state=f_data.get("state", "raw"),
            approximate=f_data.get("approximate", False),
            allergens_verified=f_data.get("allergens_verified", True),
            data_source=f_data["data_source"],
            source_reference=f_data.get("source_reference"),
            verified_at=verified_at_val,
        )
        session.add(food)
        await session.flush()

        # Add nutrients
        nutrients = f_data.get("nutrients", {})
        for code, amount in nutrients.items():
            unit = "kcal" if "kcal" in code else "g"
            fn = FoodNutrient(
                food_id=food.id,
                nutrient_code=code,
                amount_per_100g=Decimal(str(amount)),
                unit=unit,
            )
            session.add(fn)

        # Add allergens
        for allergen in f_data.get("allergens", []):
            fa = FoodAllergen(
                food_id=food.id,
                allergen_code=allergen.strip().lower(),
            )
            session.add(fa)

        existing_foods[name_lower] = food
        all_foods_by_name[name_clean] = food
        inserted_count += 1

    return inserted_count, all_foods_by_name


async def seed_recipes(session: AsyncSession, foods_by_name: dict[str, Food]) -> int:
    """Load curated recipes into database idempotently (AC-51, AC-52)."""
    with open(DATA_DIR / "recipes.json", encoding="utf-8") as f:
        recipes_data = json.load(f)

    existing_result = await session.execute(
        select(Recipe.name).where(Recipe.owner_user_id.is_(None))
    )
    existing_names = {row[0].strip().lower() for row in existing_result.all()}

    inserted_count = 0
    for r_data in recipes_data:
        name_clean = r_data["name"].strip()
        if name_clean.lower() in existing_names:
            continue

        ingredients = r_data.get("ingredients", [])
        if len(ingredients) < 2:
            raise ValueError(f"Recipe '{name_clean}' must have at least 2 ingredients")

        servings = Decimal(str(r_data.get("servings", 1.0)))
        if servings <= Decimal("0"):
            raise ValueError(f"Recipe '{name_clean}' must have servings > 0")

        prep_min = r_data.get("prep_minutes", 0)
        cook_min = r_data.get("cook_minutes", 0)
        if prep_min < 0 or cook_min < 0:
            raise ValueError(f"Recipe '{name_clean}' has negative prep or cook time")

        recipe = Recipe(
            name=name_clean,
            cuisine_code=r_data["cuisine_code"],
            instructions=r_data.get("instructions", ""),
            prep_minutes=prep_min,
            cook_minutes=cook_min,
            servings=servings,
            cost_minor_per_serving=r_data.get("cost_minor_per_serving"),
            cost_currency=r_data.get("cost_currency", "INR"),
            source_note=r_data.get("source_note"),
            owner_user_id=None,
        )
        session.add(recipe)
        await session.flush()

        # Add ingredients
        for ing in ingredients:
            food_name = ing.get("food_name")
            food_obj = foods_by_name.get(food_name) if food_name else None
            food_id = food_obj.id if food_obj else None

            qty = Decimal(str(ing["quantity"]))
            edible_weight = (
                Decimal(str(ing["edible_weight_g"]))
                if ing.get("edible_weight_g") is not None
                else None
            )

            rec_ing = RecipeIngredient(
                recipe_id=recipe.id,
                food_id=food_id,
                ingredient_name=ing["ingredient_name"],
                quantity=qty,
                unit=ing["unit"],
                edible_weight_g=edible_weight,
            )
            session.add(rec_ing)

        # Add diet tags
        for tag in r_data.get("diet_tags", []):
            dt = RecipeDietTag(
                recipe_id=recipe.id,
                diet_tag=tag.strip().lower(),
            )
            session.add(dt)

        # Add meal types
        for mt in r_data.get("meal_types", []):
            rmt = RecipeMealType(
                recipe_id=recipe.id,
                meal_type=mt.strip().lower(),
            )
            session.add(rmt)

        existing_names.add(name_clean.lower())
        inserted_count += 1

    return inserted_count


async def run_seed(session: AsyncSession) -> dict[str, int]:
    """Execute complete seed process and return counts of inserted entities."""
    ex_count = await seed_exercises(session)
    food_count, foods_by_name = await seed_foods(session)
    rec_count = await seed_recipes(session, foods_by_name)
    await session.commit()
    return {
        "exercises_inserted": ex_count,
        "foods_inserted": food_count,
        "recipes_inserted": rec_count,
    }
