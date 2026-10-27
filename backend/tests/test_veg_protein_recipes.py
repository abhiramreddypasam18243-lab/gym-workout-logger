"""Vegetarian protein recipes (2026-10-20): egg- and meat-free Indian dishes with >= 18 g protein per serving."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.seed.loader import run_seed
from tests.test_acceptance_gaps import add_goal, make_user, session_factory  # noqa: F401

DATA = Path(__file__).resolve().parent.parent / "app" / "seed" / "data"
RECIPES = {r["name"]: r for r in json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))}
FOODS = {f["name"]: f for f in json.loads((DATA / "foods.json").read_text(encoding="utf-8"))}
VEG_PROTEIN = [
    "Tofu Bhurji with Atta Roti",
    "Dahi Oats Bowl with Almonds",
    "Quinoa Vegetable Upma with Paneer",
    "Palak Paneer with Brown Rice",
    "Paneer Tikka with Peppers",
    "Chana Paneer Salad",
]
NOT_VEGETARIAN_ALLERGENS = {"eggs", "fish", "crustaceans"}
MEAT_WORDS = ("chicken", "beef", "turkey", "salmon", "shrimp", "tuna", "egg")


def _protein_per_serving(recipe: dict) -> Decimal:
    total = sum(
        Decimal(str(FOODS[i["food_name"]]["nutrients"]["protein_g"])) * Decimal(str(i["quantity"])) / 100
        for i in recipe["ingredients"]
    )
    return total / Decimal(str(recipe["servings"]))


def test_veg_protein_recipes_are_vegetarian_and_high_protein():
    for name in VEG_PROTEIN:
        r = RECIPES[name]
        assert {"vegetarian", "high_protein"} <= set(r["diet_tags"]), name
        for ing in r["ingredients"]:
            food = FOODS[ing["food_name"]]  # every ingredient is a catalogue food
            assert not set(food["allergens"]) & NOT_VEGETARIAN_ALLERGENS, (name, food["name"])
            assert not any(w in food["name"].lower() for w in MEAT_WORDS), (name, food["name"])
        assert _protein_per_serving(r) >= 18, name


def test_vegetarian_breakfasts_without_eggs_increased():
    veg_breakfasts = [
        r for r in RECIPES.values()
        if "vegetarian" in r["diet_tags"] and "breakfast" in r["meal_types"]
        and not any("egg" in (i.get("food_name") or "").lower() for i in r["ingredients"])
    ]
    assert len(veg_breakfasts) >= 5


@pytest.mark.asyncio
async def test_vegetarian_users_plan_uses_only_vegetarian_recipes(session_factory):  # noqa: F811
    async with session_factory() as db:
        await run_seed(db)
    user, client = await make_user(session_factory, "veg@example.com")
    await add_goal(session_factory, user.id)
    async with client:
        prefs = await client.patch("/api/nutrition/preferences", json={"diet_tags": ["vegetarian"]})
        assert prefs.status_code == 200
        res = await client.post("/api/meal-plans/generate", json={"start_date": "2026-10-20", "days": 7})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    for m in data["meals"]:
        # A vegan recipe is vegetarian too (D-35)
        assert {"vegetarian", "vegan"} & set(RECIPES[m["title"]]["diet_tags"]), m["title"]
