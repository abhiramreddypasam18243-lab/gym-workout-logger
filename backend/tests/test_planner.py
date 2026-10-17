"""Tests for deterministic 7-day meal plan generator (AC-56 to AC-72)."""

import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.main import app
from app.models.base import Base
from app.models.nutrition import (
    Food,
    FoodAllergen,
    FoodNutrient,
    MealPlan,
    NutritionGoal,
    PlannedMeal,
    PlannedMealItem,
    Recipe,
    RecipeIngredient,
)
from sqlalchemy.orm import selectinload
from app.models.user import Session, User, UserCuisinePreference, UserFoodConstraint, UserProfile
from app.seed.loader import run_seed
from app.services.security import generate_csrf_token, generate_session_token, hash_token


@pytest_asyncio.fixture
async def seeded_planner_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Seed catalogue
        await run_seed(session)

        # Create an adult user
        user = User(
            email="planner_user@example.com",
            password_hash="test_argon2_hash",
        )
        session.add(user)
        await session.flush()

        profile = UserProfile(
            user_id=user.id,
            display_name="Planner User",
            timezone="UTC",
            adult_confirmed_at=datetime.now(UTC),
            birth_date=date(1995, 5, 20),
            nutrition_paused=False,
            calories_hidden=False,
        )
        session.add(profile)
        await session.flush()

        # Create active nutrition target
        goal = NutritionGoal(
            user_id=user.id,
            effective_from=date(2026, 10, 1),
            calorie_target_kcal=2400,
            protein_target_g=150,
            carbs_target_g=280,
            fat_target_g=75,
            rationale="Hypertrophy target",
        )
        session.add(goal)

        # Create valid session
        raw_session_token = generate_session_token()
        raw_csrf_token = generate_csrf_token()
        user_session = Session(
            user_id=user.id,
            token_hash=hash_token(raw_session_token),
            csrf_token_hash=hash_token(raw_csrf_token),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(user_session)
        await session.commit()

        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"session_id": raw_session_token},
            headers={"X-CSRF-Token": raw_csrf_token},
        ) as client:
            yield client, session, user, goal

        app.dependency_overrides.clear()
    await engine.dispose()


async def get_recipe_with_relations(session: AsyncSession, recipe_id: UUID) -> Recipe:
    stmt = (
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.ingredients)
            .selectinload(RecipeIngredient.food)
            .selectinload(Food.allergens),
            selectinload(Recipe.diet_tags),
        )
    )
    res = await session.execute(stmt)
    return res.scalar_one()


# ---------------------------------------------------------------------------
# AC-56: Determinism Over 20 Runs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_56_determinism_over_20_runs(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    payload = {
        "start_date": "2026-10-19",
        "days": 7,
        "meal_slots": ["breakfast", "lunch", "dinner", "snack"],
    }

    first_run_recipes = None

    for i in range(20):
        resp = await client.post("/api/meal-plans/generate", json=payload)
        assert resp.status_code == 200, f"Run {i} failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "ok"

        current_run_recipes = [
            (m["plan_date"], m["meal_type"], m["recipe_id"], str(m["servings"]))
            for m in data["meals"]
        ]

        if first_run_recipes is None:
            first_run_recipes = current_run_recipes
        else:
            assert current_run_recipes == first_run_recipes, f"Run {i} differed from first run!"


# ---------------------------------------------------------------------------
# AC-57: Allergen Property Test (14 EU Allergens)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_57_allergen_property_test(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    allergens = [
        "cereals_gluten",
        "crustaceans",
        "eggs",
        "fish",
        "peanuts",
        "soybeans",
        "milk",
        "tree_nuts",
        "celery",
        "mustard",
        "sesame",
        "sulphites",
        "lupin",
        "molluscs",
    ]

    for allergen in allergens:
        # Clear previous constraints and set this allergen
        await session.execute(
            UserFoodConstraint.__table__.delete().where(UserFoodConstraint.user_id == user.id)
        )
        session.add(
            UserFoodConstraint(
                user_id=user.id,
                constraint_type="allergy",
                constraint_value=allergen,
            )
        )
        await session.commit()

        resp = await client.post(
            "/api/meal-plans/generate",
            json={"start_date": "2026-10-19", "days": 3, "meal_slots": ["lunch", "dinner"]},
        )
        assert resp.status_code == 200
        data = resp.json()

        if data["status"] == "ok":
            for meal in data["meals"]:
                rec_id = meal["recipe_id"]
                if rec_id:
                    recipe = await get_recipe_with_relations(session, UUID(rec_id))
                    # Check recipe ingredients foods allergens
                    for ing in recipe.ingredients:
                        if ing.food:
                            for fa in ing.food.allergens:
                                assert (
                                    fa.allergen_code.lower() != allergen.lower()
                                ), f"Plan contained recipe {recipe.name} with allergen {allergen}!"


# ---------------------------------------------------------------------------
# AC-58: Unverified Allergens Excluded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_58_unverified_allergens_excluded(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    # Add any allergy constraint
    session.add(
        UserFoodConstraint(
            user_id=user.id,
            constraint_type="allergy",
            constraint_value="peanuts",
        )
    )
    await session.commit()

    resp = await client.post(
        "/api/meal-plans/generate",
        json={"start_date": "2026-10-19", "days": 3, "meal_slots": ["lunch", "dinner"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    # Verify no recipe has text-only ingredients or unverified allergen foods
    for meal in data["meals"]:
        rec_id = meal["recipe_id"]
        recipe = await get_recipe_with_relations(session, UUID(rec_id))
        for ing in recipe.ingredients:
            assert ing.food_id is not None, f"Recipe {recipe.name} had text-only ingredient!"
            assert ing.food.allergens_verified is True


# ---------------------------------------------------------------------------
# AC-59: Diet Tags and Excluded Ingredients
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_59_diet_tags_and_excluded_ingredients(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    # 1. Vegetarian diet constraint + exclude "tomato"
    session.add(
        UserFoodConstraint(
            user_id=user.id,
            constraint_type="diet_tag",
            constraint_value="vegetarian",
        )
    )
    session.add(
        UserFoodConstraint(
            user_id=user.id,
            constraint_type="excluded_ingredient",
            constraint_value="tomato",
        )
    )
    await session.commit()

    resp = await client.post(
        "/api/meal-plans/generate",
        json={"start_date": "2026-10-19", "days": 3, "meal_slots": ["lunch", "dinner"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    for meal in data["meals"]:
        rec_id = meal["recipe_id"]
        recipe = await get_recipe_with_relations(session, UUID(rec_id))
        # Check vegetarian
        tags = {dt.diet_tag.lower() for dt in recipe.diet_tags}
        assert "vegetarian" in tags, f"Non-vegetarian recipe {recipe.name} found in plan!"
        # Check no tomato
        for ing in recipe.ingredients:
            assert "tomato" not in ing.ingredient_name.lower()
            if ing.food:
                assert "tomato" not in ing.food.name.lower()


# ---------------------------------------------------------------------------
# AC-60: Time Cap and Budget Limits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_60_time_cap(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    # Cap prep+cook to 30 minutes
    resp = await client.post(
        "/api/meal-plans/generate",
        json={
            "start_date": "2026-10-19",
            "days": 4,
            "meal_slots": ["lunch", "dinner"],
            "max_minutes": 30,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    for meal in data["meals"]:
        rec = await session.get(Recipe, UUID(meal["recipe_id"]))
        total_m = rec.prep_minutes + rec.cook_minutes
        assert total_m <= 30, f"Recipe {rec.name} took {total_m} mins > 30 mins cap!"


# ---------------------------------------------------------------------------
# AC-61: Cuisine Preference and Warnings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_61_cuisine_preference_warning(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    # Set Indian as avoid, Italian as favorite
    session.add(
        UserCuisinePreference(
            user_id=user.id,
            cuisine_code="indian",
            preference_level="avoid",
        )
    )
    session.add(
        UserCuisinePreference(
            user_id=user.id,
            cuisine_code="italian",
            preference_level="preferred",
        )
    )
    await session.commit()

    resp = await client.post(
        "/api/meal-plans/generate",
        json={"start_date": "2026-10-19", "days": 3, "meal_slots": ["lunch", "dinner"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "warnings" in data


# ---------------------------------------------------------------------------
# AC-62 & AC-72: Infeasible Explanation Block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_62_infeasible_explanation_block(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    # Impossible max_minutes cap: 5 minutes (no recipe is <= 5 mins)
    resp = await client.post(
        "/api/meal-plans/generate",
        json={
            "start_date": "2026-10-19",
            "days": 1,
            "meal_slots": ["lunch"],
            "max_minutes": 5,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "infeasible"
    assert data["slot"] == "lunch"
    assert data["day"] == "2026-10-19"
    assert "filters" in data
    assert "relaxable" in data
    assert "max_minutes" in data["relaxable"]
    # Rule S9, AC-62: relaxable never contains an allergy or diet restriction!
    assert "allergy" not in str(data["relaxable"])
    assert "diet" not in str(data["relaxable"])

    # Verify no meal_plan row stored
    plans = (await session.execute(select(MealPlan).where(MealPlan.user_id == user.id))).scalars().all()
    assert len(plans) == 0


# ---------------------------------------------------------------------------
# AC-66: Repetition Limits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_66_repetition_limits(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    resp = await client.post(
        "/api/meal-plans/generate",
        json={"start_date": "2026-10-19", "days": 7, "meal_slots": ["lunch"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    lunch_recipes = [m["recipe_id"] for m in data["meals"] if m["meal_type"] == "lunch"]

    # No consecutive days in the same slot
    for i in range(1, len(lunch_recipes)):
        assert (
            lunch_recipes[i] != lunch_recipes[i - 1]
        ), f"Consecutive repetition in slot: {lunch_recipes[i]}"

    # No recipe appears more than twice in 7 days for the same slot
    from collections import Counter

    counts = Counter(lunch_recipes)
    for rec_id, count in counts.items():
        assert count <= 2, f"Recipe {rec_id} appeared {count} times > 2 in 7-day lunch slot!"


# ---------------------------------------------------------------------------
# AC-67: Target Deviation Warnings and Day Totals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_67_day_totals_equal_sum_of_meals(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    resp = await client.post(
        "/api/meal-plans/generate",
        json={
            "start_date": "2026-10-19",
            "days": 7,
            "meal_slots": ["breakfast", "lunch", "dinner", "snack"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    for day in data["days"]:
        p_date = day["plan_date"]
        day_meals = [m for m in data["meals"] if m["plan_date"] == p_date]

        sum_cal = sum((Decimal(str(m["nutrients"]["calories"])) for m in day_meals), Decimal("0"))
        sum_prot = sum(
            (Decimal(str(m["nutrients"]["protein_g"])) for m in day_meals), Decimal("0")
        )

        assert Decimal(str(day["calories"])) == sum_cal
        assert Decimal(str(day["protein_g"])) == sum_prot


# ---------------------------------------------------------------------------
# AC-68: Target Snapshot Recorded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_68_target_snapshot_recorded(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    resp = await client.post(
        "/api/meal-plans/generate",
        json={"start_date": "2026-10-19", "days": 3, "meal_slots": ["breakfast", "lunch"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    snapshot = data["target_snapshot"]
    assert snapshot is not None
    assert "targets" in snapshot
    assert snapshot["targets"]["calorie_target_kcal"] == goal.calorie_target_kcal
    assert snapshot["targets"]["protein_target_g"] == goal.protein_target_g
    assert "weights" in snapshot
    assert "catalog_version" in snapshot


# ---------------------------------------------------------------------------
# AC-69: Targets Required Check (422)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_69_targets_required(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    # Delete goals
    await session.execute(
        NutritionGoal.__table__.delete().where(NutritionGoal.user_id == user.id)
    )
    await session.commit()

    resp = await client.post(
        "/api/meal-plans/generate",
        json={"start_date": "2026-10-19", "days": 7},
    )
    assert resp.status_code == 422
    assert "targets_required" in resp.text


# ---------------------------------------------------------------------------
# AC-70: Performance (<= 2 seconds at p95)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_70_performance_under_2_seconds(seeded_planner_client):
    client, session, user, goal = seeded_planner_client

    payload = {
        "start_date": "2026-10-19",
        "days": 7,
        "meal_slots": ["breakfast", "lunch", "dinner", "snack"],
    }

    start = time.perf_counter()
    resp = await client.post("/api/meal-plans/generate", json=payload)
    duration = time.perf_counter() - start

    assert resp.status_code == 200
    assert duration < 2.0, f"Generation took {duration:.3f}s (exceeded 2.0s limit)!"
