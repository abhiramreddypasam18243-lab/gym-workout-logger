"""Planner data fixes: oats carry gluten, diet tag corrections, planned item names (D-35, AC-126)

- EU Regulation 1169/2011 Annex II lists oats among the cereals containing gluten,
  so the catalogue's Rolled Oats get the `gluten` allergen (S9).
- Eggs are not vegetarian in this catalogue (D-35): the egg-white quesadilla loses
  `vegetarian`. Peanut Butter Banana Toast and Tofu Bhurji contain no animal food,
  so they gain `vegan` (the only vegan breakfasts).
- Catalogue recipe ingredients saved without their food are linked to it (see
  relink_seed_ingredients).
- Planned meal items keep the recipe's ingredient name, so text-only ingredients
  are no longer shown or merged as "Ingredient".

Revision ID: 007_planner_data_fixes
Revises: 006_muscle_set_targets
Create Date: 2026-10-28
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "007_planner_data_fixes"
down_revision: str | None = "006_muscle_set_targets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GLUTEN_FOODS = ["Rolled Oats"]
REMOVE_TAGS = [("Black Bean & Egg White Breakfast Quesadilla", "vegetarian")]
ADD_TAGS = [
    ("Peanut Butter Banana Toast", "vegan"),
    ("Tofu Bhurji with Atta Roti", "vegan"),
]


def relink_seed_ingredients() -> None:
    """Link catalogue recipe ingredients that were saved without their food.

    The seed loader looked up foods already in the database by their original name
    while it stored them by lower-case name, so recipes added after the first seed got
    `food_id = NULL` (no nutrients, unknown allergens). This links them as the seed
    file says.
    """
    recipes_path = Path(__file__).resolve().parents[2] / "app" / "seed" / "data" / "recipes.json"
    recipes = json.loads(recipes_path.read_text(encoding="utf-8"))
    for recipe in recipes:
        for ing in recipe.get("ingredients", []):
            if not ing.get("food_name"):
                continue
            op.execute(
                sa.text(
                    "UPDATE recipe_ingredients SET food_id = ("
                    "  SELECT f.id FROM foods f"
                    "  WHERE lower(f.name) = lower(:food) AND f.owner_user_id IS NULL)"
                    " WHERE food_id IS NULL AND ingredient_name = :ing"
                    " AND recipe_id IN (SELECT r.id FROM recipes r"
                    "   WHERE r.name = :recipe AND r.owner_user_id IS NULL)"
                ).bindparams(food=ing["food_name"], ing=ing["ingredient_name"], recipe=recipe["name"])
            )


def upgrade() -> None:
    relink_seed_ingredients()
    op.add_column(
        "planned_meal_items", sa.Column("ingredient_name", sa.String(200), nullable=True)
    )
    op.execute(
        sa.text(
            "UPDATE planned_meal_items SET ingredient_name = ("
            " SELECT ri.ingredient_name FROM recipe_ingredients ri"
            " WHERE ri.recipe_id = planned_meal_items.recipe_id"
            " AND (ri.food_id = planned_meal_items.food_id"
            "      OR (ri.food_id IS NULL AND planned_meal_items.food_id IS NULL))"
            " ORDER BY ri.ingredient_name LIMIT 1)"
        )
    )

    for name in GLUTEN_FOODS:
        op.execute(
            sa.text(
                "INSERT INTO food_allergens (food_id, allergen_code)"
                " SELECT f.id, 'gluten' FROM foods f"
                " WHERE f.name = :name AND f.owner_user_id IS NULL"
                " AND NOT EXISTS (SELECT 1 FROM food_allergens fa"
                "   WHERE fa.food_id = f.id AND fa.allergen_code = 'gluten')"
            ).bindparams(name=name)
        )

    for recipe, tag in REMOVE_TAGS:
        op.execute(
            sa.text(
                "DELETE FROM recipe_diet_tags WHERE diet_tag = :tag AND recipe_id IN"
                " (SELECT id FROM recipes WHERE name = :recipe AND owner_user_id IS NULL)"
            ).bindparams(tag=tag, recipe=recipe)
        )

    for recipe, tag in ADD_TAGS:
        op.execute(
            sa.text(
                "INSERT INTO recipe_diet_tags (recipe_id, diet_tag)"
                " SELECT r.id, :tag FROM recipes r"
                " WHERE r.name = :recipe AND r.owner_user_id IS NULL"
                " AND NOT EXISTS (SELECT 1 FROM recipe_diet_tags t"
                "   WHERE t.recipe_id = r.id AND t.diet_tag = :tag)"
            ).bindparams(tag=tag, recipe=recipe)
        )


def downgrade() -> None:
    # The allergen and tag corrections stay: reverting them would re-break hard filters
    op.drop_column("planned_meal_items", "ingredient_name")
