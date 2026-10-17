"""Tests for intake logging, snapshots, and planned vs logged comparison (spec §5.8, FR-12, AC-82–84)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import uuid

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.services.security import generate_csrf_token, generate_session_token, hash_token
from app.domain.comparison import compare_planned_vs_logged
from app.main import app
from app.models.base import Base
from app.models.nutrition import (
    Food,
    FoodAllergen,
    FoodNutrient,
    MealPlan,
    NutritionGoal,
    NutritionLog,
    NutritionLogItem,
    PlannedMeal,
    PlannedMealItem,
    Recipe,
    RecipeIngredient,
)
from app.models.user import Session, User, UserProfile


@pytest.fixture
async def seeded_log_client():
    """Setup test database with food, recipe, goal, and active plan for logging tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 1. Create user and adult profile
        user = User(
            email=f"loguser_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="argon2id$hashed",
        )
        session.add(user)
        await session.flush()

        profile = UserProfile(
            user_id=user.id,
            display_name="Log Tester",
            timezone="UTC",
            adult_confirmed_at=datetime.now(UTC),
            birth_date=date(1996, 4, 15),
            nutrition_paused=False,
            calories_hidden=False,
        )
        session.add(profile)

        # 2. Add fixture foods (F1, F2 from AC-47)
        # F1: 150 kcal, 25g protein, 0g carb, 5g fat per 100g. Default serving: 150g
        f1 = Food(
            name="Chicken Breast Fixture",
            food_category="protein",
            serving_description="1 breast",
            default_serving_g=Decimal("150.0"),
            data_source="verified",
            verified_at=datetime.now(UTC),
            allergens_verified=True,
        )
        session.add(f1)
        await session.flush()

        session.add_all([
            FoodNutrient(food_id=f1.id, nutrient_code="energy_kcal", amount_per_100g=Decimal("150.0"), unit="kcal"),
            FoodNutrient(food_id=f1.id, nutrient_code="protein_g", amount_per_100g=Decimal("25.0"), unit="g"),
            FoodNutrient(food_id=f1.id, nutrient_code="carbs_g", amount_per_100g=Decimal("0.0"), unit="g"),
            FoodNutrient(food_id=f1.id, nutrient_code="fat_g", amount_per_100g=Decimal("5.0"), unit="g"),
        ])

        # F2: 350 kcal, 8g protein, 75g carbs, 1g fat per 100g. Default serving: 50g
        f2 = Food(
            name="Brown Rice Fixture",
            food_category="grains",
            serving_description="1 cup dry",
            default_serving_g=Decimal("50.0"),
            data_source="verified",
            verified_at=datetime.now(UTC),
            allergens_verified=True,
        )
        session.add(f2)
        await session.flush()

        session.add_all([
            FoodNutrient(food_id=f2.id, nutrient_code="energy_kcal", amount_per_100g=Decimal("350.0"), unit="kcal"),
            FoodNutrient(food_id=f2.id, nutrient_code="protein_g", amount_per_100g=Decimal("8.0"), unit="g"),
            FoodNutrient(food_id=f2.id, nutrient_code="carbs_g", amount_per_100g=Decimal("75.0"), unit="g"),
            FoodNutrient(food_id=f2.id, nutrient_code="fat_g", amount_per_100g=Decimal("1.0"), unit="g"),
        ])

        # 3. Add fixture recipe (200g F1 + 100g F2, 2 servings -> 325 kcal, 29g protein, 37.5g carb, 5.5g fat)
        rec = Recipe(
            name="Chicken & Rice Bowl",
            cuisine_code="international",
            servings=Decimal("2.0"),
            prep_minutes=15,
            cook_minutes=20,
        )
        session.add(rec)
        await session.flush()

        session.add_all([
            RecipeIngredient(recipe_id=rec.id, food_id=f1.id, ingredient_name="Chicken Breast", quantity=Decimal("200.0"), unit="g"),
            RecipeIngredient(recipe_id=rec.id, food_id=f2.id, ingredient_name="Brown Rice", quantity=Decimal("100.0"), unit="g"),
        ])

        # 4. Add target goal
        goal = NutritionGoal(
            user_id=user.id,
            effective_from=date(2026, 10, 1),
            calorie_target_kcal=2900,
            protein_target_g=125,
            rationale="Strength building",
        )
        session.add(goal)

        # 5. Add planned meal plan for 2026-10-19 with 2900 kcal & 125g protein
        plan = MealPlan(
            user_id=user.id,
            name="Test Target Plan",
            start_date=date(2026, 10, 19),
            end_date=date(2026, 10, 25),
            status="ok",
        )
        session.add(plan)
        await session.flush()

        pm = PlannedMeal(
            meal_plan_id=plan.id,
            plan_date=date(2026, 10, 19),
            meal_type="lunch",
            title="Planned Target Meal",
            servings=Decimal("1.0"),
        )
        session.add(pm)
        await session.flush()

        # Item contributing 2900 kcal & 125g protein
        session.add(
            PlannedMealItem(
                planned_meal_id=pm.id,
                food_id=f1.id,
                quantity=Decimal("100.0"),
                unit="g",
                nutrient_snapshot={
                    "energy_kcal": "2900",
                    "protein_g": "125",
                    "carbs_g": "200",
                    "fat_g": "60",
                },
            )
        )

        # 6. Session tokens
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
            yield client, session, user, f1, f2, rec, plan

        app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# AC-82: Logging by Food and by Recipe with Snapshot Recomputation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_82_logging_food_and_recipe_with_snapshots(seeded_log_client):
    """AC-82: Logging by food (grams or servings) or recipe (servings) stores quantity & nutrient snapshot.

    Editing or deleting a log updates all totals.
    """
    client, session, user, f1, f2, rec, plan = seeded_log_client

    # 1. Log by food in grams (100g of F1 -> 150 kcal, 25g protein)
    # AND log by food in servings (2 servings of F2 = 2 * 50g = 100g -> 350 kcal, 8g protein)
    res_food = await client.post(
        "/api/nutrition/logs",
        json={
            "consumed_at": "2026-10-19T12:30:00Z",
            "meal_type": "lunch",
            "notes": "Post workout lunch",
            "items": [
                {"food_id": str(f1.id), "quantity": 100.0, "unit": "g"},
                {"food_id": str(f2.id), "quantity": 2.0, "unit": "serving"},
            ],
        },
    )
    assert res_food.status_code == 201
    log_data = res_food.json()
    assert log_data["meal_type"] == "lunch"
    assert len(log_data["items"]) == 2

    # Check totals: 150 + 350 = 500 kcal, 25 + 8 = 33g protein
    assert Decimal(str(log_data["total_calories"])) == Decimal("500")
    assert Decimal(str(log_data["total_protein_g"])) == Decimal("33")

    # Verify nutrient snapshots exist
    for it in log_data["items"]:
        assert it["nutrient_snapshot"] is not None
        assert "energy_kcal" in it["nutrient_snapshot"]

    log_id = log_data["id"]

    # 2. Log by recipe (1 serving of Chicken & Rice Bowl -> 325 kcal, 29g protein)
    res_rec = await client.post(
        "/api/nutrition/logs",
        json={
            "consumed_at": "2026-10-19T19:00:00Z",
            "meal_type": "dinner",
            "items": [
                {"recipe_id": str(rec.id), "quantity": 1.0, "unit": "serving"},
            ],
        },
    )
    assert res_rec.status_code == 201
    rec_log = res_rec.json()
    assert Decimal(str(rec_log["total_calories"])) == Decimal("325")
    assert Decimal(str(rec_log["total_protein_g"])) == Decimal("29")

    # 3. Update log item: change F1 quantity from 100g to 200g (300 kcal, 50g protein)
    # New totals: 300 + 350 = 650 kcal, 50 + 8 = 58g protein
    res_patch = await client.patch(
        f"/api/nutrition/logs/{log_id}",
        json={
            "items": [
                {"food_id": str(f1.id), "quantity": 200.0, "unit": "g"},
                {"food_id": str(f2.id), "quantity": 2.0, "unit": "serving"},
            ],
        },
    )
    assert res_patch.status_code == 200
    patched_data = res_patch.json()
    assert Decimal(str(patched_data["total_calories"])) == Decimal("650")
    assert Decimal(str(patched_data["total_protein_g"])) == Decimal("58")

    # 4. Delete log (AC-82)
    res_del = await client.delete(f"/api/nutrition/logs/{log_id}")
    assert res_del.status_code == 204

    # Confirm 404 after deletion
    res_get = await client.get(f"/api/nutrition/logs/{log_id}")
    assert res_get.status_code == 404


# ---------------------------------------------------------------------------
# AC-83: Planned vs Logged Numerical Evaluation & Neutral Labels
# ---------------------------------------------------------------------------


def test_ac_83_comparison_mathematics_and_neutral_labels():
    """AC-83: For planned day of 2900 kcal and 125g protein, and logs totalling 2610 kcal and 140g protein:

    - Difference is -290 kcal (-10.0%) and +15g (+12.0%)
    - Day is 'within range' (10% limit is inclusive)
    - Labels are strictly neutral
    """
    res = compare_planned_vs_logged(
        planned_calories=Decimal("2900"),
        planned_protein=Decimal("125"),
        logged_calories=Decimal("2610"),
        logged_protein=Decimal("140"),
    )

    # Difference = logged - planned
    assert res.calories_diff == Decimal("-290")
    assert res.calories_diff_pct == Decimal("-10.0")

    assert res.protein_diff_g == Decimal("15")
    assert round(res.protein_diff_pct, 1) == Decimal("12.0")

    # AC-83: 10% limit is inclusive -> within range!
    assert res.is_within_range is True
    assert res.status_label == "Within target range"

    # Verify neutrality: no banned words
    for banned in ["cheat", "bad", "failed", "guilt", "streak lost", "sinful", "binge"]:
        assert banned not in res.status_label.lower()


@pytest.mark.asyncio
async def test_ac_83_planned_vs_logged_api_endpoint(seeded_log_client):
    """AC-83 via API: query /api/analytics/nutrition across the planned date."""
    client, session, user, f1, f2, rec, plan = seeded_log_client

    # On 2026-10-19, planned is 2900 kcal and 125g protein.
    # We log items totalling 2610 kcal and 140g protein.
    # To log 2610 kcal: create log item with snapshot
    log_res = await client.post(
        "/api/nutrition/logs",
        json={
            "consumed_at": "2026-10-19T13:00:00Z",
            "meal_type": "lunch",
            "items": [
                {"food_id": str(f1.id), "quantity": 100.0, "unit": "g"},
            ],
        },
    )
    assert log_res.status_code == 201

    # Overwrite snapshot with exact AC-83 values for testing mathematical equivalence
    stmt = (
        select(NutritionLog)
        .where(NutritionLog.user_id == user.id)
        .options(selectinload(NutritionLog.items))
    )
    log = (await session.execute(stmt)).scalars().first()
    log.items[0].nutrient_snapshot = {
        "energy_kcal": "2610",
        "protein_g": "140",
        "carbs_g": "300",
        "fat_g": "70",
    }
    await session.commit()

    # Query analytics
    analytics_res = await client.get(
        "/api/analytics/nutrition",
        params={"start_date": "2026-10-19", "end_date": "2026-10-19"},
    )
    assert analytics_res.status_code == 200
    data = analytics_res.json()

    assert data["days_logged_count"] == 1
    day = data["days"][0]
    assert day["date"] == "2026-10-19"
    assert day["is_logged"] is True
    assert Decimal(str(day["planned_calories"])) == Decimal("2900")
    assert Decimal(str(day["logged_calories"])) == Decimal("2610")
    assert Decimal(str(day["calories_difference"])) == Decimal("-290")
    assert Decimal(str(day["calories_difference_pct"])) == Decimal("-10")
    assert Decimal(str(day["protein_difference_g"])) == Decimal("15")
    assert day["is_within_range"] is True
    assert day["status_label"] == "Within target range"


# ---------------------------------------------------------------------------
# AC-84: Unlogged Days Excluded from Averages and Timezone Assignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_84_unlogged_days_excluded_from_averages(seeded_log_client):
    """AC-84: A day with no logs is 'not logged' and excluded from averages, never shown as zero intake.

    consumed_at is assigned to days in the user's timezone.
    """
    client, session, user, f1, f2, rec, plan = seeded_log_client

    # Log only for day 2026-10-20 (500 kcal, 33g protein)
    await client.post(
        "/api/nutrition/logs",
        json={
            "consumed_at": "2026-10-20T12:00:00Z",
            "meal_type": "lunch",
            "items": [
                {"food_id": str(f1.id), "quantity": 100.0, "unit": "g"},
                {"food_id": str(f2.id), "quantity": 2.0, "unit": "serving"},
            ],
        },
    )

    # Query across 3 days: 2026-10-19 to 2026-10-21
    analytics_res = await client.get(
        "/api/analytics/nutrition",
        params={"start_date": "2026-10-19", "end_date": "2026-10-21"},
    )
    assert analytics_res.status_code == 200
    data = analytics_res.json()

    # 1 day logged out of 3
    assert data["days_logged_count"] == 1
    # Average logged calories is 500 (NOT 500 / 3 = 166.7 kcal!)
    assert Decimal(str(data["average_logged_calories"])) == Decimal("500")

    days = {d["date"]: d for d in data["days"]}

    # 2026-10-19: Unlogged day
    assert days["2026-10-19"]["is_logged"] is False
    assert days["2026-10-19"]["logged_calories"] is None
    assert days["2026-10-19"]["status_label"] == "Not logged"

    # 2026-10-20: Logged day
    assert days["2026-10-20"]["is_logged"] is True
    assert Decimal(str(days["2026-10-20"]["logged_calories"])) == Decimal("500")

    # 2026-10-21: Unlogged day
    assert days["2026-10-21"]["is_logged"] is False
    assert days["2026-10-21"]["logged_calories"] is None
    assert days["2026-10-21"]["status_label"] == "Not logged"
