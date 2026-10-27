"""AC-126 (D-35, D-36): diet-generator fixes found in review.

- Catalogue recipes added to a database that already had its foods were seeded with
  no linked foods (zero nutrients, unknown allergens).
- Oats carry gluten (EU Annex II); diet tags follow the ingredients and imply each other.
- Avoided cuisines, same-day repeats, removal counts, reloaded warnings and ingredient
  names, meal-slot validation, and the hard checks on substitutions and manual edits.
"""

import json
from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.nutrition import Food, Recipe, RecipeIngredient
from app.models.user import UserCuisinePreference, UserFoodConstraint
from app.seed.loader import run_seed, seed_foods, validate_recipe_diet_tags
from tests.test_acceptance_gaps import add_goal, make_user, session_factory  # noqa: F401

DATA = Path(__file__).resolve().parent.parent / "app" / "seed" / "data"
FOODS = {f["name"].lower(): f for f in json.loads((DATA / "foods.json").read_text(encoding="utf-8"))}
RECIPES = json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))
CUISINE_OF = {r["name"]: r["cuisine_code"] for r in RECIPES}
START = {"start_date": "2026-11-02", "days": 7}


async def _seeded_user(factory, email, constraints=(), cuisines=()):
    async with factory() as db:
        await run_seed(db)
        await db.commit()
    user, client = await make_user(factory, email)
    await add_goal(factory, user.id)
    async with factory() as db:
        for ctype, value in constraints:
            db.add(UserFoodConstraint(user_id=user.id, constraint_type=ctype, constraint_value=value))
        for code, level in cuisines:
            db.add(UserCuisinePreference(user_id=user.id, cuisine_code=code, preference_level=level))
        await db.commit()
    return user, client


@pytest.mark.asyncio
async def test_ac_126_recipes_seeded_after_foods_are_linked_to_them(session_factory):  # noqa: F811
    # The live database got its foods first; recipes added later must still link to them
    async with session_factory() as db:
        await seed_foods(db)
        await db.commit()
    async with session_factory() as db:
        await run_seed(db)
        await db.commit()
    async with session_factory() as db:
        rows = (
            await db.execute(select(Recipe).options(selectinload(Recipe.ingredients)))
        ).scalars().all()
    by_name = {r.name: r for r in rows}
    for recipe in RECIPES:
        linked = {i.ingredient_name: i.food_id for i in by_name[recipe["name"]].ingredients}
        for ing in recipe["ingredients"]:
            if ing.get("food_name"):
                assert linked[ing["ingredient_name"]] is not None, (recipe["name"], ing["ingredient_name"])


@pytest.mark.asyncio
async def test_ac_126_oats_carry_gluten_and_gluten_allergy_removes_them(session_factory):  # noqa: F811
    _, client = await _seeded_user(session_factory, "oats@example.com", [("allergy", "gluten")])
    async with session_factory() as db:
        oats = (
            await db.execute(
                select(Food).where(Food.name == "Rolled Oats").options(selectinload(Food.allergens))
            )
        ).scalar_one()
        oat_recipes = set(
            (
                await db.execute(
                    select(Recipe.name).join(RecipeIngredient).where(RecipeIngredient.food_id == oats.id)
                )
            ).scalars()
        )
    assert "gluten" in {a.allergen_code for a in oats.allergens}
    assert oat_recipes
    async with client:
        data = (await client.post("/api/meal-plans/generate", json=START)).json()
    assert data["status"] == "ok"
    assert not {m["title"] for m in data["meals"]} & oat_recipes


def test_ac_126_seed_diet_tags_match_ingredients():
    for recipe in RECIPES:
        validate_recipe_diet_tags(recipe, FOODS)  # raises on a contradiction
    egg_veg = {
        "name": "Egg Toast",
        "diet_tags": ["vegetarian"],
        "ingredients": [{"food_name": "Whole Egg"}, {"food_name": "Whole Wheat Bread"}],
    }
    with pytest.raises(ValueError, match="contradicting diet tags"):
        validate_recipe_diet_tags(egg_veg, FOODS)
    with pytest.raises(ValueError, match="gluten_free"):
        validate_recipe_diet_tags({**egg_veg, "diet_tags": ["gluten_free"]}, FOODS)


@pytest.mark.asyncio
@pytest.mark.parametrize("diet", ["vegan", "vegetarian", "pescatarian"])
async def test_ac_126_each_offered_diet_gives_a_plan_that_respects_it(session_factory, diet):  # noqa: F811
    _, client = await _seeded_user(session_factory, f"{diet}@example.com", [("diet_tag", diet)])
    async with client:
        data = (await client.post("/api/meal-plans/generate", json=START)).json()
    assert data["status"] == "ok", data
    allowed = {"vegan"} if diet == "vegan" else {"vegan", "vegetarian"}
    if diet == "pescatarian":
        allowed.add("pescatarian")
    for meal in data["meals"]:
        recipe = next(r for r in RECIPES if r["name"] == meal["title"])
        assert set(recipe["diet_tags"]) & allowed, (diet, meal["title"])


@pytest.mark.asyncio
async def test_ac_126_avoided_cuisine_only_when_nothing_else_fits(session_factory):  # noqa: F811
    _, client = await _seeded_user(
        session_factory, "avoid@example.com", cuisines=[("indian", "avoid"), ("italian", "preferred")]
    )
    async with client:
        data = (await client.post("/api/meal-plans/generate", json=START)).json()
    assert data["status"] == "ok"
    assert all(CUISINE_OF[m["title"]] != "indian" for m in data["meals"])

    # Avoiding every cuisine still gives a plan, with the warning (AC-61)
    _, client2 = await _seeded_user(
        session_factory,
        "avoid.all@example.com",
        cuisines=[(c, "avoid") for c in ("indian", "italian", "mexican", "american", "east_asian")],
    )
    async with client2:
        data2 = (await client2.post("/api/meal-plans/generate", json=START)).json()
    assert data2["status"] == "ok"
    notice = next(w for w in data2["warnings"] if w["warning"] == "cuisine_preference_unmet")
    assert notice["used_avoided_cuisine"] is True


@pytest.mark.asyncio
async def test_ac_126_counts_reload_names_and_no_same_day_repeat(session_factory):  # noqa: F811
    _, client = await _seeded_user(
        session_factory, "reload@example.com", cuisines=[("italian", "preferred")]
    )
    async with client:
        data = (await client.post("/api/meal-plans/generate", json=START)).json()
        assert data["status"] == "ok"

        # Removal counts are distinct recipes, not summed over the 28 slots
        for c in data["explanation"]["constraints_applied"]:
            assert c["removed_count"] <= len(RECIPES), c

        per_day = Counter((m["plan_date"], m["recipe_id"]) for m in data["meals"])
        assert max(per_day.values()) == 1

        again = (await client.get(f"/api/meal-plans/{data['id']}")).json()
    assert again["warnings"] == data["warnings"]
    assert any(w["warning"] == "cuisine_preference_unmet" for w in again["warnings"])
    generated = sorted(i["ingredient_name"] for m in data["meals"] for i in m["items"])
    reloaded = sorted(i["ingredient_name"] for m in again["meals"] for i in m["items"])
    assert reloaded == generated
    assert "Ingredient" not in reloaded


@pytest.mark.asyncio
async def test_ac_126_meal_slots_are_known_unique_and_ordered(session_factory):  # noqa: F811
    _, client = await _seeded_user(session_factory, "slots@example.com")
    async with client:
        for bad in (["brunch"], ["lunch", "lunch"]):
            res = await client.post("/api/meal-plans/generate", json={**START, "meal_slots": bad})
            assert res.status_code == 422, bad
        res = await client.post(
            "/api/meal-plans/generate", json={**START, "days": 1, "meal_slots": ["snack", "Breakfast"]}
        )
    meals = sorted(res.json()["meals"], key=lambda m: m["sort_order"])
    assert [m["meal_type"] for m in meals] == ["breakfast", "snack"]


@pytest.mark.asyncio
async def test_ac_126_manual_edit_and_substitution_keep_diet_and_exclusions(session_factory):  # noqa: F811
    user, client = await _seeded_user(
        session_factory, "edit@example.com", [("diet_tag", "vegetarian"), ("excluded_ingredient", "paneer")]
    )
    async with session_factory() as db:
        chicken = (
            await db.execute(select(Recipe).where(Recipe.name == "Classic Grilled Chicken with Sweet Potato & Broccoli"))
        ).scalar_one()
        paneer = (
            await db.execute(select(Recipe).where(Recipe.name == "Palak Paneer with Brown Rice"))
        ).scalar_one()
    async with client:
        plan = (await client.post("/api/meal-plans/generate", json=START)).json()
        lunch = next(m for m in plan["meals"] if m["meal_type"] == "lunch")
        res = await client.patch(
            f"/api/meal-plans/{plan['id']}/meals/{lunch['id']}", json={"recipe_id": str(chicken.id)}
        )
        assert res.status_code == 422
        assert res.json()["detail"]["code"] == "violates_hard_constraint"
        assert res.json()["detail"]["constraint"] == "diet:vegetarian"

        res = await client.post(
            f"/api/meal-plans/{plan['id']}/substitutions/accept",
            json={"meal_id": lunch["id"], "recipe_id": str(paneer.id)},
        )
        assert res.status_code == 422
        assert res.json()["detail"]["constraint"] == "excluded:paneer"


@pytest.mark.asyncio
async def test_ac_126_missing_targets_has_a_code(session_factory):  # noqa: F811
    async with session_factory() as db:
        await run_seed(db)
        await db.commit()
    _, client = await make_user(session_factory, "notargets@example.com")
    async with client:
        res = await client.post("/api/meal-plans/generate", json=START)
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "targets_required"
