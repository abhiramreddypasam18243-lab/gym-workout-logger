"""AC-121 (D-31): user allergies and catalogue foods share the 14 EU allergen codes.

The settings screen used to save `soybeans` and `cereals_gluten` while foods are tagged
`soy` and `gluten`, so the planner's exact-match allergy filter silently let them through.
"""

import json
from datetime import date
from pathlib import Path

import pytest

from app.domain.allergens import EU_ALLERGENS, normalize_allergen
from app.models.user import UserFoodConstraint
from app.seed.loader import run_seed, validate_food_allergens
from tests.test_acceptance_gaps import add_goal, make_user, session_factory  # noqa: F401

DATA = Path(__file__).resolve().parent.parent / "app" / "seed" / "data"
FOODS = {f["name"]: f for f in json.loads((DATA / "foods.json").read_text(encoding="utf-8"))}
RECIPES = json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))


def _recipes_with(allergen: str) -> set[str]:
    return {
        r["name"]
        for r in RECIPES
        if any(allergen in FOODS.get(i.get("food_name") or "", {}).get("allergens", []) for i in r["ingredients"])
    }


def test_ac_121_every_catalogue_allergen_is_one_of_the_14_codes():
    assert len(EU_ALLERGENS) == 14
    for food in FOODS.values():
        validate_food_allergens(food)  # raises on an unknown code
    with pytest.raises(ValueError, match="unknown allergen"):
        validate_food_allergens({"name": "Tofu", "allergens": ["soybeans"]})


def test_ac_121_legacy_spellings_map_to_catalogue_codes():
    assert normalize_allergen("soybeans") == "soy"
    assert normalize_allergen("cereals_gluten") == "gluten"
    assert normalize_allergen(" Tree Nuts ") == "tree_nuts"
    assert normalize_allergen("chocolate") is None


@pytest.mark.asyncio
async def test_ac_121_preferences_store_catalogue_codes_and_reject_unknown(session_factory):  # noqa: F811
    _, client = await make_user(session_factory, "allergy.codes@example.com")
    async with client:
        res = await client.patch(
            "/api/nutrition/preferences", json={"allergies": ["soybeans", "cereals_gluten", "Milk", "soy"]}
        )
        assert res.status_code == 200, res.text
        assert sorted(res.json()["allergies"]) == ["gluten", "milk", "soy"]

        bad = await client.patch("/api/nutrition/preferences", json={"allergies": ["chocolate"]})
        assert bad.status_code == 422
        assert bad.json()["detail"]["code"] == "unknown_allergen"
        # The rejected request changed nothing
        assert sorted((await client.get("/api/nutrition/preferences")).json()["allergies"]) == ["gluten", "milk", "soy"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", ["soy", "soybeans"])
async def test_ac_121_soy_allergy_removes_soy_recipes(session_factory, stored):  # noqa: F811
    soy_recipes = _recipes_with("soy")
    assert soy_recipes, "catalogue should contain soy recipes for this test"
    async with session_factory() as db:
        await run_seed(db)
    user, client = await make_user(session_factory, f"{stored}@example.com")
    await add_goal(session_factory, user.id)
    # A row saved before the fix keeps its old spelling until the migration runs; it must still filter
    async with session_factory() as db:
        db.add(UserFoodConstraint(user_id=user.id, constraint_type="allergy", constraint_value=stored))
        await db.commit()
    async with client:
        res = await client.post("/api/meal-plans/generate", json={"start_date": date.today().isoformat(), "days": 7})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "ok"
    assert not {m["title"] for m in data["meals"]} & soy_recipes
    applied = {c["filter"]: c["removed_count"] for c in data["explanation"]["constraints_applied"]}
    assert applied.get("allergy:soy", 0) > 0
