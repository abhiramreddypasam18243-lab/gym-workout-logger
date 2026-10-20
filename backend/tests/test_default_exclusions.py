"""D-27: new accounts start with beef excluded; the exclusion is an ordinary, removable preference."""

import json
from datetime import date
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.seed.loader import run_seed
from tests.test_acceptance_gaps import session_factory  # noqa: F401  (shared PostgreSQL fixture)

RECIPES = json.loads(
    (Path(__file__).resolve().parent.parent / "app" / "seed" / "data" / "recipes.json").read_text(
        encoding="utf-8"
    )
)
BEEF_RECIPES = {
    r["name"]
    for r in RECIPES
    if any(
        "beef" in (i.get("ingredient_name", "") + " " + (i.get("food_name") or "")).lower()
        for i in r["ingredients"]
    )
}


async def _register_adult_with_goal(client: AsyncClient) -> None:
    creds = {"email": "new.lifter@example.com", "password": "a long enough password"}
    assert (await client.post("/api/auth/register", json=creds)).status_code == 201
    login = await client.post("/api/auth/login", json=creds)
    assert login.status_code == 200
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    assert (await client.post("/api/profile/confirm-adult")).status_code == 200
    goal = await client.post(
        "/api/nutrition/goals", json={"calorie_target_kcal": 2400, "protein_target_g": 150}
    )
    assert goal.status_code == 201


@pytest.mark.asyncio
async def test_d27_new_account_excludes_beef_by_default_and_can_remove_it(session_factory):  # noqa: F811
    assert len(BEEF_RECIPES) >= 1, "seed catalogue should contain beef recipes for this test"
    async with session_factory() as db:
        await run_seed(db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _register_adult_with_goal(client)
        prefs = await client.get("/api/nutrition/preferences")
        assert prefs.status_code == 200
        assert prefs.json()["excluded_ingredients"] == ["beef"]

        plan = await client.post("/api/meal-plans/generate", json={"start_date": date.today().isoformat(), "days": 7})
        assert plan.status_code == 200
        data = plan.json()
        assert data["status"] == "ok"
        assert not {m["title"] for m in data["meals"]} & BEEF_RECIPES
        applied = {c["filter"]: c["removed_count"] for c in data["explanation"]["constraints_applied"]}
        assert applied.get("excluded:beef", 0) > 0

        # The user can remove the default like any other exclusion
        cleared = await client.patch("/api/nutrition/preferences", json={"excluded_ingredients": []})
        assert cleared.status_code == 200
        assert cleared.json()["excluded_ingredients"] == []
        plan2 = await client.post("/api/meal-plans/generate", json={"start_date": date.today().isoformat(), "days": 7})
        assert plan2.status_code == 200
        filters2 = {c["filter"] for c in plan2.json()["explanation"]["constraints_applied"]}
        assert "excluded:beef" not in filters2
