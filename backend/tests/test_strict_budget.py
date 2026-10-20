"""AC-120 (D-30): with a daily budget, chosen serving sizes keep every meal and day within budget."""

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.domain.scoring import ALLOWED_SERVING_SIZES, affordable_serving_sizes
from app.models.nutrition import Recipe
from app.seed.loader import run_seed
from tests.test_acceptance_gaps import add_goal, make_user, session_factory  # noqa: F401

SLOT_SHARE = {"breakfast": Decimal("0.25"), "lunch": Decimal("0.30"), "dinner": Decimal("0.30"), "snack": Decimal("0.15")}
DAILY_BUDGET = 15000  # Rs 150


def test_affordable_serving_sizes_worked_examples():
    # Rs 40/serving, breakfast share of Rs 150 = Rs 37.50: only 0.5 (Rs 20) fits; 1.0 is Rs 40
    assert affordable_serving_sizes(4000, Decimal("3750")) == (Decimal("0.5"),)
    # Rs 20/serving: 0.5 = 10, 1.0 = 20, 1.5 = 30 fit; 2.0 = 40 does not
    assert affordable_serving_sizes(2000, Decimal("3750")) == (Decimal("0.5"), Decimal("1.0"), Decimal("1.5"))
    # No budget, or a recipe without a cost: every size is allowed
    assert affordable_serving_sizes(2000, None) == ALLOWED_SERVING_SIZES
    assert affordable_serving_sizes(None, Decimal("3750")) == ALLOWED_SERVING_SIZES


async def _budget_plan(session_factory):  # noqa: F811
    async with session_factory() as db:
        await run_seed(db)
        costs = {r.id: r.cost_minor_per_serving for r in (await db.execute(select(Recipe))).scalars()}
    user, client = await make_user(session_factory, "strict.budget@example.com")
    await add_goal(session_factory, user.id)  # 2,400 kcal target: hard to reach on Rs 150
    return costs, client


@pytest.mark.asyncio
async def test_ac_120_every_meal_and_day_fits_the_daily_budget(session_factory):  # noqa: F811
    costs, client = await _budget_plan(session_factory)
    async with client:
        res = await client.post(
            "/api/meal-plans/generate",
            json={"start_date": date.today().isoformat(), "days": 7, "daily_budget_minor": DAILY_BUDGET},
        )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "ok"

    per_day: dict[str, Decimal] = defaultdict(Decimal)
    for m in data["meals"]:
        meal_cost = Decimal(costs[uuid.UUID(m["recipe_id"])]) * Decimal(str(m["servings"]))
        assert meal_cost <= Decimal(DAILY_BUDGET) * SLOT_SHARE[m["meal_type"]], m["title"]
        per_day[m["plan_date"]] += meal_cost
    assert len(per_day) == 7
    assert all(total <= DAILY_BUDGET for total in per_day.values()), per_day


@pytest.mark.asyncio
async def test_ac_120_substitutes_respect_the_plans_budget(session_factory):  # noqa: F811
    costs, client = await _budget_plan(session_factory)
    async with client:
        plan = (
            await client.post(
                "/api/meal-plans/generate",
                json={"start_date": date.today().isoformat(), "days": 1, "daily_budget_minor": DAILY_BUDGET},
            )
        ).json()
        for meal in plan["meals"]:
            res = await client.post(
                f"/api/meal-plans/{plan['id']}/substitutions/suggest", json={"meal_id": meal["id"]}
            )
            assert res.status_code == 200, res.text
            for opt in res.json():
                cost = Decimal(costs[uuid.UUID(opt["recipe_id"])]) * Decimal(str(opt["servings"]))
                assert cost <= Decimal(DAILY_BUDGET) * SLOT_SHARE[meal["meal_type"]], opt["recipe_name"]
