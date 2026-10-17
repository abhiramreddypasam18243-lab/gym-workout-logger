"""Tests for catalogue seeding, validators, search, snapshots, and constraints (AC-48 to AC-55)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base
from app.models.nutrition import (
    Food,
    FoodNutrient,
    NutritionLog,
    NutritionLogItem,
    Recipe,
    RecipeIngredient,
)
from app.models.user import Session, User
from app.models.workout import Exercise
from app.seed.loader import (
    run_seed,
    validate_food_atwater,
    validate_food_provenance,
)
from app.services.security import generate_csrf_token, generate_session_token, hash_token


@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_client(test_db: AsyncSession):
    # Seed the test DB
    await run_seed(test_db)

    # Dependency override for FastAPI get_db
    from app.api.deps import get_db

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, test_db

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC-48: Database Check Constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_48_database_check_constraints(test_db: AsyncSession):
    # 1. Negative nutrient amount rejected
    food = Food(
        name="Test Food",
        food_category="test",
        serving_description="100g",
        state="raw",
        data_source="Test",
        verified_at=date.today(),
    )
    test_db.add(food)
    await test_db.flush()

    fn = FoodNutrient(
        food_id=food.id,
        nutrient_code="protein_g",
        amount_per_100g=Decimal("-5.0"),  # Negative!
        unit="g",
    )
    test_db.add(fn)
    with pytest.raises(IntegrityError):
        await test_db.flush()
    await test_db.rollback()

    # 2. Non-positive recipe servings rejected
    recipe = Recipe(
        name="Invalid Recipe",
        cuisine_code="italian",
        instructions="Cook",
        servings=Decimal("0.0"),  # Non-positive!
    )
    test_db.add(recipe)
    with pytest.raises(IntegrityError):
        await test_db.flush()
    await test_db.rollback()

    # 3. Non-positive ingredient quantity rejected
    recipe_valid = Recipe(
        name="Valid Recipe",
        cuisine_code="italian",
        instructions="Cook",
        servings=Decimal("1.0"),
    )
    test_db.add(recipe_valid)
    await test_db.flush()

    ing = RecipeIngredient(
        recipe_id=recipe_valid.id,
        ingredient_name="Salt",
        quantity=Decimal("-1.0"),  # Non-positive!
        unit="g",
    )
    test_db.add(ing)
    with pytest.raises(IntegrityError):
        await test_db.flush()
    await test_db.rollback()


# ---------------------------------------------------------------------------
# AC-49: Food Provenance Validation & Approximate Labelling
# ---------------------------------------------------------------------------


def test_ac_49_food_provenance_validation():
    # Complete food dictionary
    valid_food = {
        "name": "Valid Oats",
        "data_source": "USDA FoodData Central",
        "serving_description": "1/2 cup (40g)",
        "state": "raw",
        "verified_at": "2026-10-16",
    }
    validate_food_provenance(valid_food)

    # Missing data_source
    invalid_1 = dict(valid_food, data_source="")
    with pytest.raises(ValueError, match="data_source"):
        validate_food_provenance(invalid_1)

    # Missing serving_description
    invalid_2 = dict(valid_food, serving_description="")
    with pytest.raises(ValueError, match="serving_description"):
        validate_food_provenance(invalid_2)

    # Missing state
    invalid_3 = dict(valid_food, state="")
    with pytest.raises(ValueError, match="state"):
        validate_food_provenance(invalid_3)

    # Missing verified_at
    invalid_4 = dict(valid_food, verified_at="")
    with pytest.raises(ValueError, match="verified_at"):
        validate_food_provenance(invalid_4)


@pytest.mark.asyncio
async def test_ac_49_approximate_flag_labelled(seeded_client):
    client, _ = seeded_client
    resp = await client.get("/api/foods")
    assert resp.status_code == 200
    foods = resp.json()
    approximate_foods = [f for f in foods if f.get("approximate") is True]
    assert len(approximate_foods) >= 1
    # Check that is_approximate is explicitly present and True
    for af in approximate_foods:
        assert af["is_approximate"] is True


# ---------------------------------------------------------------------------
# AC-50: Atwater 4-4-9 Energy Balance Check
# ---------------------------------------------------------------------------


def test_ac_50_atwater_check():
    # Valid food: Chicken Breast (165 kcal, 31P, 0C, 3.6F)
    chicken = {
        "name": "Chicken Breast",
        "approximate": False,
        "nutrients": {
            "energy_kcal": 165.0,
            "protein_g": 31.0,
            "carbs_g": 0.0,
            "fat_g": 3.6,
        },
    }
    validate_food_atwater(chicken)

    # Inconsistent food
    fraud_food = {
        "name": "Bogus Protein Powder",
        "approximate": False,
        "nutrients": {
            "energy_kcal": 400.0,
            "protein_g": 10.0,
            "carbs_g": 10.0,
            "fat_g": 2.0,
        },
    }
    with pytest.raises(ValueError, match="violates Atwater"):
        validate_food_atwater(fraud_food)

    # Approximate foods skip Atwater verification
    approx_food = dict(fraud_food, approximate=True)
    validate_food_atwater(approx_food)


# ---------------------------------------------------------------------------
# AC-51: Idempotency, Row Counts, and Integrity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_51_seed_idempotency_and_counts(test_db: AsyncSession):
    # First seed run
    first_res = await run_seed(test_db)
    assert 30 <= first_res["exercises_inserted"] <= 50
    assert 40 <= first_res["foods_inserted"] <= 60
    assert 15 <= first_res["recipes_inserted"] <= 25

    # Count database rows
    ex_count_1 = (await test_db.execute(select(Exercise))).scalars().all()
    food_count_1 = (await test_db.execute(select(Food))).scalars().all()
    rec_count_1 = (await test_db.execute(select(Recipe))).scalars().all()

    # Second seed run must be idempotent (zero new rows inserted)
    second_res = await run_seed(test_db)
    assert second_res["exercises_inserted"] == 0
    assert second_res["foods_inserted"] == 0
    assert second_res["recipes_inserted"] == 0

    ex_count_2 = (await test_db.execute(select(Exercise))).scalars().all()
    food_count_2 = (await test_db.execute(select(Food))).scalars().all()
    rec_count_2 = (await test_db.execute(select(Recipe))).scalars().all()

    assert len(ex_count_1) == len(ex_count_2)
    assert len(food_count_1) == len(food_count_2)
    assert len(rec_count_1) == len(rec_count_2)

    # Verify at least 4 cuisines are covered
    cuisines = {r.cuisine_code for r in rec_count_1}
    assert len(cuisines) >= 4


# ---------------------------------------------------------------------------
# AC-52: Recipe Allergen Union & Incomplete Allergen Flagging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_52_recipe_allergen_union(seeded_client):
    client, _ = seeded_client

    # 1. Check an Italian recipe containing pasta (gluten) and parmesan (milk)
    resp = await client.get("/api/recipes", params={"q": "Chicken & Broccoli Penne with Parmesan"})
    assert resp.status_code == 200
    recipes = resp.json()
    assert len(recipes) == 1
    recipe = recipes[0]
    assert "gluten" in recipe["allergens"]
    assert "milk" in recipe["allergens"]
    assert recipe["has_incomplete_allergen_data"] is False

    # 2. Check recipe with text-only ingredient: has_incomplete_allergen_data == True
    resp_power = await client.get("/api/recipes", params={"q": "Power Bowl"})
    assert resp_power.status_code == 200
    p_recipes = resp_power.json()
    assert len(p_recipes) == 1
    power_bowl = p_recipes[0]
    assert power_bowl["has_incomplete_allergen_data"] is True


# ---------------------------------------------------------------------------
# AC-53: Catalogue Search, Filters, and Custom Exercises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_53_catalogue_search_and_filters(seeded_client):
    client, db = seeded_client

    # 1. Search exercise by substring
    resp = await client.get("/api/exercises?q=squat")
    assert resp.status_code == 200
    squats = resp.json()
    assert len(squats) >= 3
    assert all("squat" in s["name"].lower() for s in squats)

    # 2. Filter exercise by muscle
    resp_chest = await client.get("/api/exercises?muscle=chest")
    assert resp_chest.status_code == 200
    assert all(e["primary_muscle"] == "chest" for e in resp_chest.json())

    # 3. Filter recipes by cuisine
    resp_ind = await client.get("/api/recipes?cuisine=indian")
    assert resp_ind.status_code == 200
    assert len(resp_ind.json()) >= 4
    assert all(r["cuisine_code"] == "indian" for r in resp_ind.json())

    # 4. Filter recipes by diet_tag
    resp_veg = await client.get("/api/recipes?diet_tag=vegetarian")
    assert resp_veg.status_code == 200
    assert len(resp_veg.json()) >= 4
    for r in resp_veg.json():
        assert "vegetarian" in r["diet_tags"]

    # 5. Filter recipes by max_time
    resp_fast = await client.get("/api/recipes?max_time=20")
    assert resp_fast.status_code == 200
    for r in resp_fast.json():
        assert r["total_minutes"] <= 20

    # 6. Custom exercise uniqueness per owner (AC-30)
    # Register a user
    user = User(
        email="lifter@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",
    )
    db.add(user)
    await db.flush()

    raw_token = generate_session_token()
    raw_csrf = generate_csrf_token()
    now = datetime.now(UTC)
    session = Session(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_token_hash=hash_token(raw_csrf),
        created_at=now,
        expires_at=now + timedelta(days=14),
    )
    db.add(session)
    await db.commit()

    # Create custom exercise
    create_resp = await client.post(
        "/api/exercises",
        json={
            "name": "Custom Zercher Squat",
            "primary_muscle": "quads",
            "equipment": "barbell",
            "movement_pattern": "squat",
            "instructions": "Hold bar in crooks of elbows",
        },
        cookies={"session_id": raw_token},
        headers={"X-CSRF-Token": raw_csrf},
    )
    assert create_resp.status_code == 201

    # Duplicate create must return 409 (AC-30)
    dup_resp = await client.post(
        "/api/exercises",
        json={
            "name": "custom zercher squat",  # case-insensitive duplicate
            "primary_muscle": "quads",
            "equipment": "barbell",
        },
        cookies={"session_id": raw_token},
        headers={"X-CSRF-Token": raw_csrf},
    )
    assert dup_resp.status_code == 409


# ---------------------------------------------------------------------------
# AC-54: Immutable Historical Snapshots
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_54_immutable_historical_snapshots(test_db: AsyncSession):
    # Create user
    user = User(
        email="snapshot@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",
    )
    test_db.add(user)
    await test_db.flush()

    # Create food
    food = Food(
        name="Snapshot Oats",
        food_category="grains",
        serving_description="100g",
        state="raw",
        data_source="USDA",
        verified_at=date.today(),
    )
    test_db.add(food)
    await test_db.flush()

    fn = FoodNutrient(
        food_id=food.id,
        nutrient_code="energy_kcal",
        amount_per_100g=Decimal("380.0"),
        unit="kcal",
    )
    test_db.add(fn)
    await test_db.flush()

    # Create historical log item with nutrient snapshot
    log = NutritionLog(
        user_id=user.id,
        consumed_at=datetime.now(UTC),
        meal_type="breakfast",
        source_type="food",
    )
    test_db.add(log)
    await test_db.flush()

    historical_snapshot = {"calories": 380, "protein_g": 13}
    item = NutritionLogItem(
        nutrition_log_id=log.id,
        food_id=food.id,
        quantity=Decimal("100"),
        unit="g",
        nutrient_snapshot=historical_snapshot,
    )
    test_db.add(item)
    await test_db.commit()

    # Now update food nutrient value in catalogue
    fn.amount_per_100g = Decimal("400.0")
    await test_db.commit()

    # Verify historical log snapshot did NOT change
    reloaded_item = await test_db.get(NutritionLogItem, item.id)
    assert reloaded_item is not None
    assert reloaded_item.nutrient_snapshot["calories"] == 380


# ---------------------------------------------------------------------------
# AC-55: Referenced Food Delete Restriction (409 Conflict)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_55_restrict_delete_referenced_food(seeded_client):
    client, db = seeded_client

    # Find a food used in recipes (e.g. Chicken Breast)
    result = await db.execute(select(Food).where(Food.name == "Chicken Breast (Raw)").limit(1))
    chicken = result.scalar_one()

    # Create user and session
    user = User(
        email="deleter@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",
    )
    db.add(user)
    await db.flush()

    raw_token = generate_session_token()
    raw_csrf = generate_csrf_token()
    now = datetime.now(UTC)
    session = Session(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_token_hash=hash_token(raw_csrf),
        created_at=now,
        expires_at=now + timedelta(days=14),
    )
    db.add(session)
    await db.commit()

    # Attempt delete -> must return 409 Conflict
    resp = await client.delete(
        f"/api/foods/{chicken.id}",
        cookies={"session_id": raw_token},
        headers={"X-CSRF-Token": raw_csrf},
    )
    assert resp.status_code == 409
