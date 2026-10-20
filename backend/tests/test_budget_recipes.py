"""Budget recipes (D-28): ten Indian recipes at <= Rs 50 per serving built only from catalogue foods."""

import json
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.main import app
from app.models.nutrition import Recipe
from app.seed.loader import run_seed
from tests.test_acceptance_gaps import add_goal, make_user, session_factory  # noqa: F401

DATA = Path(__file__).resolve().parent.parent / "app" / "seed" / "data"
RECIPES = json.loads((DATA / "recipes.json").read_text(encoding="utf-8"))
FOOD_NAMES = {f["name"] for f in json.loads((DATA / "foods.json").read_text(encoding="utf-8"))}
BUDGET = [r for r in RECIPES if "budget_friendly" in r["diet_tags"]]
SLOT_SHARE = {"breakfast": Decimal("0.25"), "lunch": Decimal("0.30"), "dinner": Decimal("0.30"), "snack": Decimal("0.15")}


def test_budget_recipes_use_only_catalogue_foods_and_cost_at_most_50_rupees():
    assert len(BUDGET) == 14  # 10 from D-28 + 4 using the USDA Indian staples (2026-10-20)
    for r in BUDGET:
        assert r["cost_minor_per_serving"] <= 5000, r["name"]
        assert r["cost_currency"] == "INR"
        for ing in r["ingredients"]:
            assert ing["food_name"] in FOOD_NAMES, (r["name"], ing["food_name"])
    slots = {mt for r in BUDGET for mt in r["meal_types"]}
    assert slots == {"breakfast", "lunch", "dinner", "snack"}


@pytest.mark.asyncio
async def test_budget_recipes_listed_in_catalogue(session_factory):  # noqa: F811
    async with session_factory() as db:
        await run_seed(db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/recipes", params={"diet_tag": "budget_friendly", "limit": 100})
        assert res.status_code == 200
        assert sorted(r["name"] for r in res.json()) == sorted(r["name"] for r in BUDGET)


@pytest.mark.asyncio
async def test_150_rupee_daily_budget_gives_a_plan_within_slot_budgets(session_factory):  # noqa: F811
    async with session_factory() as db:
        await run_seed(db)
        costs = {r.id: r.cost_minor_per_serving for r in (await db.execute(select(Recipe))).scalars()}
    user, client = await make_user(session_factory, "budget@example.com")
    await add_goal(session_factory, user.id)
    daily_budget = 15000  # Rs 150 a day
    async with client:
        res = await client.post(
            "/api/meal-plans/generate",
            json={"start_date": "2026-10-20", "days": 7, "daily_budget_minor": daily_budget},
        )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "ok"
    # Every chosen recipe passes the planner's budget cap (spec 5.5 step 1.4): half a serving
    # must fit the slot's share of the daily budget
    for m in data["meals"]:
        slot_budget = Decimal(daily_budget) * SLOT_SHARE[m["meal_type"]]
        assert Decimal(costs[uuid.UUID(m["recipe_id"])]) * Decimal("0.5") <= slot_budget


@pytest.mark.asyncio
async def test_seed_adds_new_recipes_to_an_existing_catalogue(session_factory):  # noqa: F811
    async with session_factory() as db:
        first = await run_seed(db)
        assert first["recipes_inserted"] == len(RECIPES)
        # An existing database that predates one recipe gets it on the next start
        await db.execute(delete(Recipe).where(Recipe.name == BUDGET[0]["name"]))
        await db.commit()
        again = await run_seed(db)
        assert again == {"exercises_inserted": 0, "foods_inserted": 0, "recipes_inserted": 1}
