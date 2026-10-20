"""Indian staples added from USDA FoodData Central (SR Legacy) on 2026-10-20."""

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.nutrition import Food
from app.seed.loader import run_seed, validate_food_atwater, validate_food_provenance
from tests.test_acceptance_gaps import session_factory  # noqa: F401

DATA = Path(__file__).resolve().parent.parent / "app" / "seed" / "data"
FOODS = {f["name"]: f for f in json.loads((DATA / "foods.json").read_text(encoding="utf-8"))}
RECIPES = {r["name"]: r for r in json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))}

NEW_FOODS = {
    "Moong Dal (Mung Beans, Raw)": ("174256", []),
    "Rajma (Red Kidney Beans, Boiled)": ("175194", []),
    "Besan (Chickpea Flour)": ("174288", []),
    "Curd (Plain Whole-Milk Yogurt)": ("171284", ["milk"]),
    "Peanuts (Raw)": ("172430", ["peanuts"]),
    "Moong Sprouts (Raw)": ("169957", []),
    "Soya Chunks (Defatted Soy Flour Values)": ("174275", ["soy"]),
}


def test_new_foods_cite_usda_fdc_ids_and_pass_provenance_and_atwater():
    for name, (fdc_id, allergens) in NEW_FOODS.items():
        food = FOODS[name]
        assert food["data_source"] == "USDA FoodData Central"
        assert food["source_reference"].startswith(f"FDC: {fdc_id} ")
        assert food["allergens"] == allergens, name
        validate_food_provenance(food)
        validate_food_atwater(food)  # no-op for approximate foods


def test_soya_chunks_are_flagged_approximate():
    # Values are USDA's defatted soy flour, the material soya chunks are made from (DL1)
    assert FOODS["Soya Chunks (Defatted Soy Flour Values)"]["approximate"] is True


def test_new_recipes_use_the_new_foods_and_are_budget_friendly():
    for name, food in [
        ("Rajma Chawal", "Rajma (Red Kidney Beans, Boiled)"),
        ("Besan Chilla with Curd", "Besan (Chickpea Flour)"),
        ("Soya Chunk Curry with Rice", "Soya Chunks (Defatted Soy Flour Values)"),
        ("Moong Dal Khichdi", "Moong Dal (Mung Beans, Raw)"),
    ]:
        r = RECIPES[name]
        assert food in {i["food_name"] for i in r["ingredients"]}
        assert "budget_friendly" in r["diet_tags"] and r["cost_minor_per_serving"] <= 5000


@pytest.mark.asyncio
async def test_new_foods_are_seeded(session_factory):  # noqa: F811
    async with session_factory() as db:
        await run_seed(db)
        names = set((await db.execute(select(Food.name))).scalars())
    assert set(NEW_FOODS) <= names
