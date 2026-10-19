"""Tests for data controls: complete user data export (AC-88) and verified account deletion (AC-89)."""

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import jsonschema
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_db
from app.main import app
from app.models.nutrition import (
    Food,
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
from app.models.user import Session, User, UserCuisinePreference, UserFoodConstraint, UserProfile
from app.models.workout import (
    Exercise,
    RoutineExercise,
    WorkoutExercise,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSet,
)
from app.schemas.data_export import get_export_json_schema
from app.services.security import (
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_token,
)
from tests.db import create_test_engine, reset_schema


@pytest.fixture
async def data_controls_client():
    """Setup test database with full user data, second tenant, and shared catalogue."""
    engine = create_test_engine()
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(reset_schema)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with async_session() as session:
        # Create User A
        raw_pw_a = "StrongSecret123!"
        user_a = User(
            id=uuid.uuid4(),
            email="usera@example.com",
            password_hash=hash_password(raw_pw_a),
            is_active=True,
            created_at=datetime.now(UTC),
        )
        session.add(user_a)

        # Profile A
        prof_a = UserProfile(
            user_id=user_a.id,
            display_name="User Alpha",
            timezone="America/New_York",
            units="kg",
            sex_for_estimate="male",
            weekly_session_target=4,
            goal="build_strength",
            activity_level="moderate",
            track_body_weight=True,
            calories_hidden=False,
            nutrition_paused=False,
            needs_professional_guidance=False,
        )
        session.add(prof_a)

        # Food Constraints A
        cons_a = UserFoodConstraint(
            id=uuid.uuid4(),
            user_id=user_a.id,
            constraint_type="allergy",
            constraint_value="peanuts",
            is_hard_constraint=True,
        )
        session.add(cons_a)

        # Cuisine Preference A
        cuis_a = UserCuisinePreference(
            id=uuid.uuid4(),
            user_id=user_a.id,
            cuisine_code="italian",
            preference_level="preferred",
        )
        session.add(cuis_a)

        # Nutrition Goal A
        goal_a = NutritionGoal(
            id=uuid.uuid4(),
            user_id=user_a.id,
            effective_from=date(2026, 10, 20),
            calorie_target_kcal=2600,
            protein_target_g=160,
            carbs_target_g=300,
            fat_target_g=70,
            rationale="Initial bulk target",
            created_at=datetime.now(UTC),
        )
        session.add(goal_a)

        # Shared Catalogue: System Exercise
        sys_ex = Exercise(
            id=uuid.uuid4(),
            name="Barbell Bench Press",
            primary_muscle="chest",
            equipment="barbell",
            owner_user_id=None,  # Shared system catalogue
        )
        session.add(sys_ex)

        # Custom Exercise for User A
        cust_ex_a = Exercise(
            id=uuid.uuid4(),
            name="Alpha Grip Pulldown",
            primary_muscle="lats",
            equipment="cable",
            owner_user_id=user_a.id,  # User-owned custom exercise
        )
        session.add(cust_ex_a)

        # Routine for User A
        rot_a = WorkoutRoutine(
            id=uuid.uuid4(),
            user_id=user_a.id,
            name="Alpha Upper Body",
            created_at=datetime.now(UTC),
        )
        session.add(rot_a)
        re_a = RoutineExercise(
            id=uuid.uuid4(),
            routine_id=rot_a.id,
            exercise_id=sys_ex.id,
            order_index=1,
            target_sets=3,
            rep_min=8,
            rep_max=12,
        )
        session.add(re_a)

        # Workout Session for User A
        ws_a = WorkoutSession(
            id=uuid.uuid4(),
            user_id=user_a.id,
            routine_id=rot_a.id,
            started_at=datetime(2026, 10, 15, 10, 0, tzinfo=UTC),
            completed_at=datetime(2026, 10, 15, 11, 0, tzinfo=UTC),
            notes="Felt strong",
        )
        session.add(ws_a)
        we_a = WorkoutExercise(
            id=uuid.uuid4(),
            session_id=ws_a.id,
            exercise_id=sys_ex.id,
            order_index=1,
        )
        session.add(we_a)
        wset_a = WorkoutSet(
            id=uuid.uuid4(),
            workout_exercise_id=we_a.id,
            set_number=1,
            reps=10,
            load_kg=Decimal("100.0"),
            rpe=Decimal("8.5"),
            is_warmup=False,
            completed_at=datetime(2026, 10, 15, 10, 15, tzinfo=UTC),
        )
        session.add(wset_a)

        # Shared Catalogue: Food & Recipe
        food = Food(
            id=uuid.uuid4(),
            name="Oatmeal Flakes",
            food_category="grains",
            serving_description="1 cup",
            default_serving_g=Decimal("80.0"),
            data_source="USDA",
        )
        session.add(food)
        fn = FoodNutrient(
            food_id=food.id,
            nutrient_code="energy_kcal",
            amount_per_100g=Decimal("380.0"),
            unit="kcal",
        )
        session.add(fn)

        recipe = Recipe(
            id=uuid.uuid4(),
            name="Power Oats",
            cuisine_code="western",
            prep_minutes=5,
            cook_minutes=5,
            servings=Decimal("1.0"),
        )
        session.add(recipe)
        ri = RecipeIngredient(
            recipe_id=recipe.id,
            food_id=food.id,
            ingredient_name="Oatmeal Flakes",
            quantity=Decimal("80.0"),
            unit="g",
        )
        session.add(ri)

        # Meal Plan for User A
        plan_a = MealPlan(
            id=uuid.uuid4(),
            user_id=user_a.id,
            start_date=date(2026, 10, 19),
            end_date=date(2026, 10, 25),
            status="ok",
            created_at=datetime.now(UTC),
        )
        session.add(plan_a)
        pm_a = PlannedMeal(
            id=uuid.uuid4(),
            meal_plan_id=plan_a.id,
            plan_date=date(2026, 10, 19),
            meal_type="breakfast",
            title="Power Oats Breakfast",
            recipe_id=recipe.id,
            servings=Decimal("1.0"),
            sort_order=0,
        )
        session.add(pm_a)
        pmi_a = PlannedMealItem(
            id=uuid.uuid4(),
            planned_meal_id=pm_a.id,
            food_id=food.id,
            quantity=Decimal("80.0"),
            unit="g",
        )
        session.add(pmi_a)

        # Nutrition Log for User A
        nlog_a = NutritionLog(
            id=uuid.uuid4(),
            user_id=user_a.id,
            consumed_at=datetime(2026, 10, 19, 8, 30, tzinfo=UTC),
            meal_type="breakfast",
            source_type="food",
            notes="Breakfast bowl",
        )
        session.add(nlog_a)
        nli_a = NutritionLogItem(
            id=uuid.uuid4(),
            nutrition_log_id=nlog_a.id,
            food_id=food.id,
            quantity=Decimal("80.0"),
            unit="g",
            nutrient_snapshot={"energy_kcal": "304", "protein_g": "10"},
        )
        session.add(nli_a)

        # User A Session
        raw_token_a = generate_session_token()
        raw_csrf_a = generate_csrf_token()
        sess_a = Session(
            user_id=user_a.id,
            token_hash=hash_token(raw_token_a),
            csrf_token_hash=hash_token(raw_csrf_a),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            created_at=datetime.now(UTC),
        )
        session.add(sess_a)

        # -------------------------------------------------------------
        # Create Second Tenant (User B) to test strict tenant isolation
        # -------------------------------------------------------------
        user_b = User(
            id=uuid.uuid4(),
            email="userb@example.com",
            password_hash=hash_password("SecretBravo456!"),
            is_active=True,
            created_at=datetime.now(UTC),
        )
        session.add(user_b)
        rot_b = WorkoutRoutine(
            id=uuid.uuid4(),
            user_id=user_b.id,
            name="Bravo Confidential Routine",
            created_at=datetime.now(UTC),
        )
        session.add(rot_b)

        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies={"session_id": raw_token_a, "csrf_token": raw_csrf_a},
        headers={"X-CSRF-Token": raw_csrf_a},
    ) as client:
        yield client, user_a, user_b, raw_pw_a, async_session

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac_88_complete_data_export_and_json_schema_validation(data_controls_client):
    """AC-88: Complete data export contains every record of every user-owned table, matches DB counts, validates against schema, and enforces tenant boundary."""
    client, user_a, user_b, raw_pw_a, async_session = data_controls_client

    res = await client.get("/api/export")
    assert res.status_code == 200
    assert "attachment; filename=" in res.headers.get("Content-Disposition", "")

    export_json = res.json()

    # 1. Validate against published JSON Schema (AC-88)
    schema = get_export_json_schema()
    # jsonschema.validate raises ValidationError if schema does not match
    jsonschema.validate(instance=export_json, schema=schema)

    # 2. Check metadata and counts matching database (AC-88)
    meta = export_json["metadata"]
    assert meta["user_id"] == str(user_a.id)
    assert meta["export_version"] == "1.0"
    counts = meta["record_counts"]
    assert counts["users"] == 1
    assert counts["user_profiles"] == 1
    assert counts["user_food_constraints"] == 1
    assert counts["user_cuisine_preferences"] == 1
    assert counts["nutrition_goals"] == 1
    assert counts["workout_routines"] == 1
    assert counts["routine_exercises"] == 1
    assert counts["workout_sessions"] == 1
    assert counts["workout_exercises"] == 1
    assert counts["workout_sets"] == 1
    assert counts["custom_exercises"] == 1
    assert counts["meal_plans"] == 1
    assert counts["planned_meals"] == 1
    assert counts["planned_meal_items"] == 1
    assert counts["nutrition_logs"] == 1
    assert counts["nutrition_log_items"] == 1

    # 3. Check data payload structure
    assert export_json["user"]["email"] == "usera@example.com"
    assert export_json["profile"]["weekly_session_target"] == 4
    assert export_json["food_constraints"][0]["constraint_value"] == "peanuts"
    assert len(export_json["workout_sessions"]) == 1
    assert export_json["workout_sessions"][0]["notes"] == "Felt strong"
    assert export_json["custom_exercises"][0]["name"] == "Alpha Grip Pulldown"

    # 4. Strict Tenant Boundary Isolation Check (SEC1, AC-88)
    # Ensure User B's confidential routine and user id do NOT appear anywhere in User A's export
    export_str = json.dumps(export_json)
    assert str(user_b.id) not in export_str
    assert "Bravo Confidential Routine" not in export_str
    assert "userb@example.com" not in export_str


@pytest.mark.asyncio
async def test_ac_89_delete_account_wrong_password_rejected(data_controls_client):
    """AC-89: Deleting account requires the correct password; invalid password rejected with 401."""
    client, user_a, user_b, raw_pw_a, async_session = data_controls_client

    # Attempt delete with wrong password
    del_res = await client.request(
        "DELETE",
        "/api/account",
        json={"password": "IncorrectPassword999!"},
    )
    assert del_res.status_code == 401
    assert del_res.json()["detail"]["code"] == "invalid_password"

    # Verify user still exists in database
    async with async_session() as session:
        u = (await session.execute(select(User).where(User.id == user_a.id))).scalar_one_or_none()
        assert u is not None


@pytest.mark.asyncio
async def test_ac_89_delete_account_removes_all_user_rows_and_leaves_shared_catalogue(data_controls_client):
    """AC-89: Verified account deletion deletes all user rows from every user-owned table, revokes session, and leaves shared catalogue intact."""
    client, user_a, user_b, raw_pw_a, async_session = data_controls_client

    # Delete account with correct password
    del_res = await client.request(
        "DELETE",
        "/api/account",
        json={"password": raw_pw_a},
    )
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # Verify every user-owned table has 0 rows for user_a
    async with async_session() as session:
        # User
        assert (await session.execute(select(func.count(User.id)).where(User.id == user_a.id))).scalar() == 0
        # Profile
        assert (await session.execute(select(func.count(UserProfile.user_id)).where(UserProfile.user_id == user_a.id))).scalar() == 0
        # Sessions
        assert (await session.execute(select(func.count(Session.id)).where(Session.user_id == user_a.id))).scalar() == 0
        # Constraints & Preferences
        assert (await session.execute(select(func.count(UserFoodConstraint.user_id)).where(UserFoodConstraint.user_id == user_a.id))).scalar() == 0
        assert (await session.execute(select(func.count(UserCuisinePreference.user_id)).where(UserCuisinePreference.user_id == user_a.id))).scalar() == 0
        # Nutrition Goals
        assert (await session.execute(select(func.count(NutritionGoal.id)).where(NutritionGoal.user_id == user_a.id))).scalar() == 0
        # Routines
        assert (await session.execute(select(func.count(WorkoutRoutine.id)).where(WorkoutRoutine.user_id == user_a.id))).scalar() == 0
        # Workout Sessions
        assert (await session.execute(select(func.count(WorkoutSession.id)).where(WorkoutSession.user_id == user_a.id))).scalar() == 0
        # Custom Exercises
        assert (await session.execute(select(func.count(Exercise.id)).where(Exercise.owner_user_id == user_a.id))).scalar() == 0
        # Meal Plans
        assert (await session.execute(select(func.count(MealPlan.id)).where(MealPlan.user_id == user_a.id))).scalar() == 0
        # Nutrition Logs
        assert (await session.execute(select(func.count(NutritionLog.id)).where(NutritionLog.user_id == user_a.id))).scalar() == 0

        # Verify Shared Catalogue is 100% INTACT (AC-89)
        # Shared system exercise remains
        sys_ex_cnt = (await session.execute(select(func.count(Exercise.id)).where(Exercise.owner_user_id.is_(None)))).scalar()
        assert sys_ex_cnt >= 1
        # Shared food remains
        food_cnt = (await session.execute(select(func.count(Food.id)))).scalar()
        assert food_cnt >= 1
        # Shared recipe remains
        recipe_cnt = (await session.execute(select(func.count(Recipe.id)))).scalar()
        assert recipe_cnt >= 1

        # Verify Second Tenant (User B) is 100% INTACT (SEC1)
        u_b = (await session.execute(select(User).where(User.id == user_b.id))).scalar_one_or_none()
        assert u_b is not None
        rot_b_cnt = (await session.execute(select(func.count(WorkoutRoutine.id)).where(WorkoutRoutine.user_id == user_b.id))).scalar()
        assert rot_b_cnt == 1

    # Verify session is revoked: subsequent API request returns 401
    followup_res = await client.get("/api/auth/me")
    assert followup_res.status_code == 401
