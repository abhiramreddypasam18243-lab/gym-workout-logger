"""Acceptance criteria that had no dedicated test: AC-05, AC-26, AC-29, AC-30, AC-65, AC-71, AC-72, AC-97.

Expected values are derived from the seed files and database rows, never from the app's output.
"""

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.config import Config
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alembic import command
from app.api.deps import get_current_session, get_db
from app.config import settings
from app.main import app
from app.models.nutrition import (
    Food,
    FoodNutrient,
    MealPlan,
    NutritionGoal,
    PlannedMeal,
    PlannedMealItem,
    Recipe,
    RecipeIngredient,
    RecipeMealType,
)
from app.models.user import Session, User, UserProfile
from app.models.workout import Exercise
from app.seed.loader import run_seed
from app.services import planner as planner_module
from app.services.security import generate_csrf_token, generate_session_token, hash_token
from tests.db import TEST_DATABASE_URL, create_test_engine, reset_schema

BACKEND_DIR = Path(__file__).resolve().parent.parent
SEED_EXERCISES = json.loads(
    (BACKEND_DIR / "app" / "seed" / "data" / "exercises.json").read_text(encoding="utf-8")
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def session_factory():
    """Fresh PostgreSQL schema; requests get their own session, committed or rolled back like get_db."""
    engine = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(reset_schema)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    yield factory
    app.dependency_overrides.clear()
    await engine.dispose()


def anon_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def make_user(factory, email: str) -> tuple[User, AsyncClient]:
    """Adult user with an active session; returns the user and an authenticated client."""
    async with factory() as db:
        user = User(email=email, password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy")
        db.add(user)
        await db.flush()
        db.add(
            UserProfile(
                user_id=user.id,
                display_name=email.split("@")[0],
                timezone="UTC",
                adult_confirmed_at=datetime.now(UTC),
                birth_date=date(1995, 5, 20),
            )
        )
        raw_token, raw_csrf = generate_session_token(), generate_csrf_token()
        now = datetime.now(UTC)
        db.add(
            Session(
                user_id=user.id,
                token_hash=hash_token(raw_token),
                csrf_token_hash=hash_token(raw_csrf),
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
        )
        await db.commit()
    client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"session_id": raw_token},
        headers={"X-CSRF-Token": raw_csrf},
    )
    return user, client


async def add_goal(factory, user_id: uuid.UUID) -> None:
    async with factory() as db:
        db.add(
            NutritionGoal(
                user_id=user_id,
                effective_from=date(2026, 10, 1),
                calorie_target_kcal=2400,
                protein_target_g=150,
                carbs_target_g=280,
                fat_target_g=75,
            )
        )
        await db.commit()


def _api_routes(routes):
    """All APIRoutes, including those inside included routers (FastAPI nests them)."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):
            yield from _api_routes(route.original_router.routes)


def _requires_session(route: APIRoute) -> bool:
    stack = list(route.dependant.dependencies)
    while stack:
        dep = stack.pop()
        if dep.call is get_current_session:
            return True
        stack.extend(dep.dependencies)
    return False


# ---------------------------------------------------------------------------
# AC-05: logout revokes the session everywhere
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_05_logout_revokes_session_on_every_endpoint(session_factory):
    async with anon_client() as client:
        reg = await client.post(
            "/api/auth/register",
            json={"email": "logout@example.com", "password": "correct horse battery"},
        )
        assert reg.status_code == 201
        login = await client.post(
            "/api/auth/login",
            json={"email": "logout@example.com", "password": "correct horse battery"},
        )
        assert login.status_code == 200
        old_cookie = login.cookies["session_id"]
        csrf = login.json()["csrf_token"]

        assert (await client.get("/api/auth/me")).status_code == 200
        out = await client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
        assert out.status_code in (200, 204)

    protected = [
        (method, route.path)
        for route in _api_routes(app.routes)
        if _requires_session(route)
        for method in sorted(route.methods)
    ]
    assert len(protected) > 20  # sanity: the whole authenticated API is covered

    fake_id = str(uuid.uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"session_id": old_cookie},
        headers={"X-CSRF-Token": csrf},
    ) as old:
        for method, path in protected:
            url = path
            for part in path.split("/"):
                if part.startswith("{") and part.endswith("}"):
                    url = url.replace(part, fake_id)
            body = {} if method in ("POST", "PATCH", "PUT") else None
            res = await old.request(method, url, json=body)
            assert res.status_code == 401, f"{method} {path} returned {res.status_code}"


# ---------------------------------------------------------------------------
# AC-26: body weight is never required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_26_no_flow_requires_body_weight(session_factory):
    async with session_factory() as db:
        await run_seed(db)
        squat = (await db.execute(select(Exercise).where(Exercise.name.ilike("%squat%")))).scalars().first()
    user, client = await make_user(session_factory, "noweight@example.com")
    async with client:
        prof = await client.patch("/api/profile", json={"track_body_weight": False})
        assert prof.status_code == 200
        assert prof.json()["track_body_weight"] is False
        assert prof.json()["body_weight_kg"] is None

        started = datetime.now(UTC) - timedelta(hours=1)
        workout = await client.post(
            "/api/workouts",
            json={
                "started_at": started.isoformat(),
                "completed_at": (started + timedelta(minutes=45)).isoformat(),
                "exercises": [
                    {
                        "exercise_id": str(squat.id),
                        "order_index": 0,
                        "sets": [
                            {
                                "set_number": 1,
                                "load_kg": "100",
                                "reps": 5,
                                "completed_at": (started + timedelta(minutes=5)).isoformat(),
                            }
                        ],
                    }
                ],
            },
        )
        assert workout.status_code == 201, workout.text

        goal = await client.post(
            "/api/nutrition/goals", json={"calorie_target_kcal": 2400, "protein_target_g": 150}
        )
        assert goal.status_code == 201, goal.text

        plan = await client.post(
            "/api/meal-plans/generate",
            json={"start_date": date.today().isoformat(), "days": 1, "meal_slots": ["breakfast", "lunch"]},
        )
        assert plan.status_code == 200, plan.text
        assert plan.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# AC-29: exercise search, filters, pagination, custom-exercise visibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_29_exercise_search_filters_pagination_visibility(session_factory):
    async with session_factory() as db:
        await run_seed(db)

    expected_squats = sorted(e["name"] for e in SEED_EXERCISES if "squat" in e["name"].lower())
    assert expected_squats, "seed catalogue must contain squat variations"

    async with anon_client() as client:
        res = await client.get("/api/exercises", params={"q": "SQUAT", "limit": 100})
        assert res.status_code == 200
        assert sorted(e["name"] for e in res.json()) == expected_squats

        muscle = SEED_EXERCISES[0]["primary_muscle"]
        equipment = SEED_EXERCISES[0]["equipment"]
        expected_filtered = sorted(
            e["name"]
            for e in SEED_EXERCISES
            if e["primary_muscle"].lower() == muscle.lower()
            and e["equipment"].lower() == equipment.lower()
        )
        res = await client.get(
            "/api/exercises", params={"muscle": muscle, "equipment": equipment, "limit": 100}
        )
        assert sorted(e["name"] for e in res.json()) == expected_filtered

        page1 = (await client.get("/api/exercises", params={"limit": 5, "offset": 0})).json()
        page2 = (await client.get("/api/exercises", params={"limit": 5, "offset": 5})).json()
        both = (await client.get("/api/exercises", params={"limit": 10, "offset": 0})).json()
        assert len(page1) == 5 and len(page2) == 5
        assert {e["id"] for e in page1}.isdisjoint({e["id"] for e in page2})
        assert [e["id"] for e in page1 + page2] == [e["id"] for e in both]

    _, owner = await make_user(session_factory, "owner@example.com")
    _, other = await make_user(session_factory, "other@example.com")
    async with owner, other, anon_client() as anon:
        created = await owner.post(
            "/api/exercises",
            json={
                "name": "Owner Special Squat",
                "primary_muscle": "quads",
                "equipment": "barbell",
                "movement_pattern": "squat",
            },
        )
        assert created.status_code == 201

        def names(r):
            return {e["name"] for e in r.json()}

        assert "Owner Special Squat" in names(await owner.get("/api/exercises", params={"q": "special"}))
        assert "Owner Special Squat" not in names(await other.get("/api/exercises", params={"q": "special"}))
        assert "Owner Special Squat" not in names(await anon.get("/api/exercises", params={"q": "special"}))


# ---------------------------------------------------------------------------
# AC-30: custom name unique per owner; seed exercises cannot be edited or deleted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_30_custom_name_unique_per_owner_and_seeds_immutable(session_factory):
    async with session_factory() as db:
        await run_seed(db)
        seed = (await db.execute(select(Exercise).where(Exercise.owner_user_id.is_(None)))).scalars().first()
        seed_id, seed_name = seed.id, seed.name

    _, a = await make_user(session_factory, "a@example.com")
    _, b = await make_user(session_factory, "b@example.com")
    body = {"name": "Tempo Pause Row", "primary_muscle": "back", "equipment": "barbell", "movement_pattern": "pull"}
    async with a, b:
        assert (await a.post("/api/exercises", json=body)).status_code == 201
        dup = await a.post("/api/exercises", json={**body, "name": "TEMPO pause ROW"})
        assert dup.status_code == 409
        # Another owner may reuse the name
        assert (await b.post("/api/exercises", json=body)).status_code == 201

        patch = await a.patch(f"/api/exercises/{seed_id}", json={"name": "Hacked"})
        delete = await a.delete(f"/api/exercises/{seed_id}")
        assert patch.status_code in (403, 404, 405)
        assert delete.status_code in (403, 404, 405)

    async with session_factory() as db:
        still = await db.get(Exercise, seed_id)
        assert still is not None and still.name == seed_name


# ---------------------------------------------------------------------------
# AC-65: equal scores are broken by recipe ID ascending
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_65_equal_scores_tie_broken_by_recipe_id(session_factory):
    low_id = uuid.UUID("00000000-0000-4000-8000-000000000001")
    high_id = uuid.UUID("ffffffff-ffff-4fff-bfff-ffffffffffff")
    async with session_factory() as db:
        food = Food(
            name="Fixture Oats (test-only values)",
            food_category="grains",
            serving_description="100 g",
            data_source="test fixture",
        )
        db.add(food)
        await db.flush()
        for code, amount in [("energy_kcal", "380"), ("protein_g", "13"), ("carbs_g", "67"), ("fat_g", "7")]:
            db.add(FoodNutrient(food_id=food.id, nutrient_code=code, amount_per_100g=Decimal(amount), unit="g"))
        # Insert the higher ID first so insertion order cannot explain the result
        for rid in (high_id, low_id):
            db.add(Recipe(id=rid, name=f"Identical Oats {rid}", cuisine_code="american", servings=Decimal("1")))
            await db.flush()
            db.add(RecipeMealType(recipe_id=rid, meal_type="breakfast"))
            db.add(
                RecipeIngredient(
                    recipe_id=rid, food_id=food.id, ingredient_name="oats", quantity=Decimal("100"), unit="g"
                )
            )
        await db.commit()

    user, client = await make_user(session_factory, "tie@example.com")
    await add_goal(session_factory, user.id)
    async with client:
        picks = []
        for _ in range(5):
            res = await client.post(
                "/api/meal-plans/generate",
                json={"start_date": "2026-10-19", "days": 1, "meal_slots": ["breakfast"]},
            )
            assert res.status_code == 200, res.text
            picks.append(res.json()["meals"][0]["recipe_id"])
    assert picks == [str(low_id)] * 5


# ---------------------------------------------------------------------------
# AC-71: saving a plan is transactional
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_71_plan_save_failure_leaves_no_partial_plan(session_factory, monkeypatch):
    async with session_factory() as db:
        await run_seed(db)
    user, client = await make_user(session_factory, "atomic@example.com")
    await add_goal(session_factory, user.id)

    real_item = planner_module.PlannedMealItem
    calls = {"n": 0}

    def failing_item(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 5:  # after the plan and several meals/items have been flushed
            raise RuntimeError("simulated failure while saving")
        return real_item(*args, **kwargs)

    monkeypatch.setattr(planner_module, "PlannedMealItem", failing_item)

    async with client:
        with pytest.raises(RuntimeError, match="simulated failure"):
            await client.post(
                "/api/meal-plans/generate",
                json={"start_date": "2026-10-19", "days": 7},
            )
    assert calls["n"] == 5

    async with session_factory() as db:
        assert (await db.scalar(select(func.count()).select_from(MealPlan))) == 0
        assert (await db.scalar(select(func.count()).select_from(PlannedMeal))) == 0
        assert (await db.scalar(select(func.count()).select_from(PlannedMealItem))) == 0


# ---------------------------------------------------------------------------
# AC-72: explanation block on every plan response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_72_explanation_block_complete(session_factory):
    async with session_factory() as db:
        await run_seed(db)
    user, client = await make_user(session_factory, "explain@example.com")
    await add_goal(session_factory, user.id)
    payload = {"start_date": "2026-10-19", "days": 3}

    async with client:
        first = await client.post("/api/meal-plans/generate", json=payload)
        assert first.status_code == 200
        # Mark one food used by the plan as approximate so the share is non-trivial
        used_food_id = next(
            it["food_id"] for m in first.json()["meals"] for it in m["items"] if it["food_id"]
        )
        async with session_factory() as db:
            food = await db.get(Food, uuid.UUID(used_food_id))
            food.approximate = True
            await db.commit()

        res = await client.post("/api/meal-plans/generate", json=payload)
        assert res.status_code == 200
        data = res.json()
        exp = data["explanation"]

        assert isinstance(exp["constraints_applied"], list)
        for c in exp["constraints_applied"]:
            assert set(c) == {"filter", "removed_count"}
        assert exp["scoring_weights"] == {"w_t": "1.0", "w_c": "0.3", "w_p": "0.2", "w_b": "0.2", "w_r": "0.5"}
        assert exp["generation_version"] and exp["catalog_version"]
        assert "not guaranteed optimal" in exp["statement"]

        # Expected share: nutrient values of the plan's items whose food is approximate / all values
        async with session_factory() as db:
            rows = (
                await db.execute(
                    select(PlannedMealItem.food_id, Food.approximate, func.count(FoodNutrient.nutrient_code))
                    .join(PlannedMeal, PlannedMealItem.planned_meal_id == PlannedMeal.id)
                    .join(Food, PlannedMealItem.food_id == Food.id)
                    .join(FoodNutrient, FoodNutrient.food_id == Food.id)
                    .where(PlannedMeal.meal_plan_id == uuid.UUID(data["id"]))
                    .group_by(PlannedMealItem.id, PlannedMealItem.food_id, Food.approximate)
                )
            ).all()
        total = sum(n for _, _, n in rows)
        approx = sum(n for _, is_approx, n in rows if is_approx)
        assert approx > 0
        assert exp["share_approximate_nutrients"] == pytest.approx(round(approx / total, 4))

        # Reading the plan later returns the same explanation
        again = await client.get(f"/api/meal-plans/{data['id']}")
        assert again.status_code == 200
        assert again.json()["explanation"] == exp


# ---------------------------------------------------------------------------
# AC-97: migrations build the schema, roll back, and match the models
# ---------------------------------------------------------------------------


def test_ac_97_migrations_upgrade_downgrade_and_no_drift(monkeypatch):
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    async def wipe() -> None:
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(wipe())
    monkeypatch.setattr(settings, "DATABASE_URL", TEST_DATABASE_URL)
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))

    command.upgrade(cfg, "head")
    command.check(cfg)  # raises if models and migrations have drifted
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    asyncio.run(wipe())
