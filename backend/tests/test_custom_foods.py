"""AC-122 (D-32): users add their own foods with per-100 g values; only the owner sees or logs them."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.nutrition import Food, RecipeIngredient
from app.seed.loader import run_seed
from tests.test_acceptance_gaps import anon_client, make_user, session_factory  # noqa: F401

# Values a user might copy from a packet label (fixture data for the test, not catalogue data)
POHA = {
    "name": "Mom's Poha",
    "serving_description": "1 plate (180 g)",
    "default_serving_g": "180",
    "state": "cooked",
    "nutrients": {"energy_kcal": "130", "protein_g": "2.5", "carbs_g": "23", "fat_g": "3.2"},
    "allergens": ["peanuts", "soybeans"],
}


def _nutrient(food: dict, code: str) -> Decimal:
    return next(Decimal(n["amount_per_100g"]) for n in food["nutrients"] if n["nutrient_code"] == code)


@pytest.mark.asyncio
async def test_ac_122_create_custom_food_is_labelled_user_entered(session_factory):  # noqa: F811
    _, client = await make_user(session_factory, "poha@example.com")
    async with client:
        res = await client.post("/api/foods", json=POHA)
        assert res.status_code == 201, res.text
        food = res.json()
        assert food["is_custom"] is True
        assert food["approximate"] is True and food["is_approximate"] is True
        assert food["allergens_verified"] is False
        assert food["data_source"] == "User-entered"
        assert sorted(food["allergens"]) == ["peanuts", "soy"]  # spelling mapped to the catalogue code
        assert _nutrient(food, "energy_kcal") == Decimal("130")
        assert _nutrient(food, "fat_g") == Decimal("3.2")

        # Same name again, any case: 409
        dup = await client.post("/api/foods", json={**POHA, "name": "MOM'S POHA"})
        assert dup.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"nutrients": {"energy_kcal": "400", "protein_g": "60", "carbs_g": "30", "fat_g": "20"}},  # 110 g of macros
        {"nutrients": {"energy_kcal": "950", "protein_g": "0", "carbs_g": "0", "fat_g": "100"}},  # above 900 kcal
        {"nutrients": {"energy_kcal": "-1", "protein_g": "0", "carbs_g": "0", "fat_g": "0"}},
        {"allergens": ["chocolate"]},
        {"owner_user_id": "00000000-0000-0000-0000-000000000000"},  # unknown fields are rejected (AC-09)
    ],
)
async def test_ac_122_invalid_custom_food_is_rejected(session_factory, change):  # noqa: F811
    _, client = await make_user(session_factory, "bad.food@example.com")
    async with client:
        res = await client.post("/api/foods", json={**POHA, **change})
        assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_ac_122_custom_food_is_private_to_its_owner(session_factory):  # noqa: F811
    _, owner = await make_user(session_factory, "owner@example.com")
    _, other = await make_user(session_factory, "other@example.com")
    async with owner, other, anon_client() as anon:
        food = (await owner.post("/api/foods", json=POHA)).json()
        url = f"/api/foods/{food['id']}"

        assert (await owner.get(url)).status_code == 200
        mine = (await owner.get("/api/foods", params={"mine": True})).json()
        assert [f["name"] for f in mine] == ["Mom's Poha"]

        for client in (other, anon):
            assert (await client.get(url)).status_code == 404
            names = [f["name"] for f in (await client.get("/api/foods", params={"q": "poha"})).json()]
            assert "Mom's Poha" not in names
        assert (await other.patch(url, json={"name": "Stolen"})).status_code == 404
        assert (await other.delete(url)).status_code == 404

        # Another user may use the same name for their own food
        assert (await other.post("/api/foods", json=POHA)).status_code == 201


@pytest.mark.asyncio
async def test_ac_122_log_custom_food_and_edits_keep_old_snapshots(session_factory):  # noqa: F811
    _, owner = await make_user(session_factory, "logger@example.com")
    _, other = await make_user(session_factory, "nosy@example.com")
    async with owner, other:
        food = (await owner.post("/api/foods", json=POHA)).json()
        entry = {
            "consumed_at": datetime.now(UTC).isoformat(),
            "meal_type": "breakfast",
            "items": [{"food_id": food["id"], "quantity": "1", "unit": "serving"}],
        }
        log = await owner.post("/api/nutrition/logs", json=entry)
        assert log.status_code == 201, log.text
        # 1 serving = 180 g; 130 kcal per 100 g x 1.8 = 234 kcal; protein 2.5 x 1.8 = 4.5 g
        assert Decimal(log.json()["total_calories"]) == Decimal("234")
        assert Decimal(log.json()["total_protein_g"]) == Decimal("4.5")

        # Someone else cannot log the owner's food
        assert (await other.post("/api/nutrition/logs", json=entry)).status_code == 404

        new_values = {"energy_kcal": "200", "protein_g": "4", "carbs_g": "30", "fat_g": "6"}
        edit = await owner.patch(f"/api/foods/{food['id']}", json={"nutrients": new_values, "allergens": []})
        assert edit.status_code == 200, edit.text
        assert _nutrient(edit.json(), "energy_kcal") == Decimal("200")
        assert edit.json()["allergens"] == []

        # The earlier log keeps the values it was logged with (AC-54)
        again = await owner.get(f"/api/nutrition/logs/{log.json()['id']}")
        assert Decimal(again.json()["total_calories"]) == Decimal("234")

        # A logged custom food cannot be deleted (AC-55); an unlogged one can
        assert (await owner.delete(f"/api/foods/{food['id']}")).status_code == 409
        spare = (await owner.post("/api/foods", json={**POHA, "name": "Spare"})).json()
        assert (await owner.delete(f"/api/foods/{spare['id']}")).status_code == 204
        assert (await owner.get(f"/api/foods/{spare['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_ac_122_catalogue_foods_are_read_only(session_factory):  # noqa: F811
    async with session_factory() as db:
        await run_seed(db)
        used = select(RecipeIngredient.food_id).where(RecipeIngredient.food_id.is_not(None))
        unused = (
            await db.execute(select(Food).where(Food.owner_user_id.is_(None), Food.id.not_in(used)))
        ).scalars().first()
        assert unused is not None, "test needs a catalogue food no recipe uses"
    _, client = await make_user(session_factory, "editor@example.com")
    async with client:
        assert (await client.patch(f"/api/foods/{unused.id}", json={"name": "Mine now"})).status_code == 403
        assert (await client.delete(f"/api/foods/{unused.id}")).status_code == 403
        assert (await client.get(f"/api/foods/{unused.id}")).json()["name"] == unused.name


@pytest.mark.asyncio
async def test_ac_122_seed_never_links_recipes_to_a_users_food(session_factory):  # noqa: F811
    # A user's food named like a catalogue food must not stand in for it when the seed runs
    _, client = await make_user(session_factory, "early@example.com")
    async with client:
        mine = (await client.post("/api/foods", json={**POHA, "name": "Chicken Breast (Raw)"})).json()
    async with session_factory() as db:
        await run_seed(db)
        named = (await db.execute(select(Food).where(Food.name == "Chicken Breast (Raw)"))).scalars().all()
        assert len(named) == 2
        catalogue = next(f for f in named if f.owner_user_id is None)
        linked = await db.execute(
            select(func.count()).select_from(RecipeIngredient).where(RecipeIngredient.food_id == mine["id"])
        )
        assert linked.scalar_one() == 0
        assert (
            await db.execute(
                select(func.count()).select_from(RecipeIngredient).where(RecipeIngredient.food_id == catalogue.id)
            )
        ).scalar_one() > 0


@pytest.mark.asyncio
async def test_ac_122_export_includes_and_account_deletion_removes_custom_foods(session_factory):  # noqa: F811
    creds = {"email": "leaver@example.com", "password": "a long enough password"}
    async with anon_client() as client:
        assert (await client.post("/api/auth/register", json=creds)).status_code == 201
        login = await client.post("/api/auth/login", json=creds)
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        assert (await client.post("/api/foods", json=POHA)).status_code == 201

        export = (await client.get("/api/me/export")).json()
        assert export["metadata"]["record_counts"]["custom_foods"] == 1
        assert export["custom_foods"][0]["name"] == "Mom's Poha"
        assert export["custom_foods"][0]["nutrients_per_100g"]["energy_kcal"] == "130.00"

        gone = await client.request("DELETE", "/api/me", json={"password": creds["password"]})
        assert gone.status_code == 200, gone.text
    async with session_factory() as db:
        assert (await db.execute(select(func.count()).select_from(Food).where(Food.owner_user_id.is_not(None)))).scalar_one() == 0
