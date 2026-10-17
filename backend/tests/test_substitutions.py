"""Tests for meal substitutions, manual edits, and unit-aware grocery lists (AC-73 to AC-81)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

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
    NutritionGoal,
    Recipe,
    RecipeIngredient,
)
from app.models.user import Session, User, UserFoodConstraint, UserProfile
from app.seed.loader import run_seed
from app.services.security import generate_csrf_token, generate_session_token, hash_token


@pytest_asyncio.fixture
async def seeded_sub_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        await run_seed(session)

        # Create user with profile
        user = User(
            email="sub_user@example.com",
            password_hash="test_argon2_hash",
        )
        session.add(user)
        await session.flush()

        profile = UserProfile(
            user_id=user.id,
            display_name="Substitution User",
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
            rationale="Strength maintenance",
        )
        session.add(goal)

        # Create session
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
            # Generate a 7-day base plan
            gen_resp = await client.post(
                "/api/meal-plans/generate",
                json={
                    "start_date": "2026-10-19",
                    "days": 7,
                    "meal_slots": ["breakfast", "lunch", "dinner", "snack"],
                },
            )
            assert gen_resp.status_code == 200
            plan_data = gen_resp.json()
            assert plan_data["status"] == "ok"

            yield client, session, user, goal, plan_data

        app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# AC-73: Substitution Suggestions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_73_substitution_suggestions(seeded_sub_client):
    client, session, user, goal, plan_data = seeded_sub_client

    plan_id = plan_data["id"]
    meal = plan_data["meals"][0]
    meal_id = meal["id"]
    current_recipe_id = meal["recipe_id"]

    resp = await client.post(
        f"/api/meal-plans/{plan_id}/substitutions/suggest",
        json={"meal_id": meal_id},
    )
    assert resp.status_code == 200
    suggestions = resp.json()

    # AC-73: At most 5 suggestions
    assert 1 <= len(suggestions) <= 5

    # AC-73: Excludes current recipe
    for s in suggestions:
        assert s["recipe_id"] != current_recipe_id
        # AC-73: Shows nutrient differences
        assert "nutrient_diff" in s
        diff = s["nutrient_diff"]
        assert "calories" in diff
        assert "protein_g" in diff
        assert "carbs_g" in diff
        assert "fat_g" in diff

    # AC-73: Ordered by score descending
    for i in range(1, len(suggestions)):
        assert Decimal(str(suggestions[i]["score"])) <= Decimal(str(suggestions[i - 1]["score"]))


# ---------------------------------------------------------------------------
# AC-74: Accepting Substitution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_74_accept_substitution(seeded_sub_client):
    client, session, user, goal, plan_data = seeded_sub_client

    plan_id = plan_data["id"]
    meal = plan_data["meals"][0]
    meal_id = meal["id"]

    # Get suggestions
    sug_resp = await client.post(
        f"/api/meal-plans/{plan_id}/substitutions/suggest",
        json={"meal_id": meal_id},
    )
    suggestions = sug_resp.json()
    chosen_sub = suggestions[0]

    # Accept substitution
    accept_resp = await client.post(
        f"/api/meal-plans/{plan_id}/substitutions/accept",
        json={
            "meal_id": meal_id,
            "recipe_id": chosen_sub["recipe_id"],
            "servings": chosen_sub["servings"],
        },
    )
    assert accept_resp.status_code == 200
    updated_plan = accept_resp.json()

    # Plan status updated to edited
    assert updated_plan["status"] == "edited"

    # Meal is updated with chosen recipe
    updated_meal = next((m for m in updated_plan["meals"] if m["id"] == meal_id), None)
    assert updated_meal is not None
    assert updated_meal["recipe_id"] == chosen_sub["recipe_id"]
    assert Decimal(str(updated_meal["servings"])) == Decimal(str(chosen_sub["servings"]))

    # Day totals equal sum of meals
    day = next((d for d in updated_plan["days"] if d["plan_date"] == updated_meal["plan_date"]), None)
    assert day is not None
    day_meals = [m for m in updated_plan["meals"] if m["plan_date"] == updated_meal["plan_date"]]
    sum_cal = sum((Decimal(str(m["nutrients"]["calories"])) for m in day_meals), Decimal("0"))
    assert Decimal(str(day["calories"])) == sum_cal


# ---------------------------------------------------------------------------
# AC-75: Manual Edit Safety Violation Rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_75_manual_edit_violates_allergy_rejected(seeded_sub_client):
    client, session, user, goal, plan_data = seeded_sub_client

    plan_id = plan_data["id"]
    meal = plan_data["meals"][0]
    meal_id = meal["id"]

    # Set user allergy to peanuts
    session.add(
        UserFoodConstraint(
            user_id=user.id,
            constraint_type="allergy",
            constraint_value="peanuts",
        )
    )
    await session.commit()

    # Find a recipe with peanuts
    # Create or find peanut recipe in catalogue
    rec_stmt = (
        select(Recipe)
        .join(Recipe.ingredients)
        .join(RecipeIngredient.food)
        .join(Food.allergens)
        .where(FoodAllergen.allergen_code == "peanuts")
    )
    peanut_rec = (await session.execute(rec_stmt)).scalars().first()

    if not peanut_rec:
        # Create a peanut test recipe
        food = Food(
            name="Peanut Butter",
            food_category="nuts",
            serving_description="32g",
            data_source="USDA",
            state="raw",
            verified_at=date.today(),
        )
        session.add(food)
        await session.flush()
        session.add(FoodAllergen(food_id=food.id, allergen_code="peanuts"))
        peanut_rec = Recipe(
            name="Peanut Snack",
            cuisine_code="american",
            servings=Decimal("1.0"),
            instructions="Mix",
        )
        session.add(peanut_rec)
        await session.flush()
        session.add(
            RecipeIngredient(
                recipe_id=peanut_rec.id,
                food_id=food.id,
                ingredient_name="Peanut Butter",
                quantity=Decimal("30.0"),
                unit="g",
            )
        )
        await session.commit()

    # Attempting to manually replace meal with peanut recipe must be rejected with 422 violates_hard_constraint
    resp = await client.patch(
        f"/api/meal-plans/{plan_id}/meals/{meal_id}",
        json={"recipe_id": str(peanut_rec.id)},
    )
    assert resp.status_code == 422
    assert "violates_hard_constraint" in resp.text


# ---------------------------------------------------------------------------
# AC-76: Servings Range and Doubling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_76_servings_range_and_doubling(seeded_sub_client):
    client, session, user, goal, plan_data = seeded_sub_client

    plan_id = plan_data["id"]
    meal = plan_data["meals"][0]
    meal_id = meal["id"]

    # 1. Reject 0, -1, 11
    for bad_s in [0, -1, 11]:
        resp = await client.patch(
            f"/api/meal-plans/{plan_id}/meals/{meal_id}",
            json={"servings": bad_s},
        )
        assert resp.status_code == 422, f"Servings {bad_s} was not rejected!"

    # 2. Accept 0.5 and 10
    resp_05 = await client.patch(
        f"/api/meal-plans/{plan_id}/meals/{meal_id}",
        json={"servings": 0.5},
    )
    assert resp_05.status_code == 200

    resp_10 = await client.patch(
        f"/api/meal-plans/{plan_id}/meals/{meal_id}",
        json={"servings": 10.0},
    )
    assert resp_10.status_code == 200

    # 3. Test changing from 1 to 2 doubles nutrients
    # Set to 1.0
    await client.patch(
        f"/api/meal-plans/{plan_id}/meals/{meal_id}",
        json={"servings": 1.0},
    )
    plan_1 = (await client.get(f"/api/meal-plans/{plan_id}")).json()
    meal_1 = next((m for m in plan_1["meals"] if m["id"] == meal_id), None)
    c1 = Decimal(str(meal_1["nutrients"]["calories"]))
    p1 = Decimal(str(meal_1["nutrients"]["protein_g"]))

    # Set to 2.0
    await client.patch(
        f"/api/meal-plans/{plan_id}/meals/{meal_id}",
        json={"servings": 2.0},
    )
    plan_2 = (await client.get(f"/api/meal-plans/{plan_id}")).json()
    meal_2 = next((m for m in plan_2["meals"] if m["id"] == meal_id), None)
    c2 = Decimal(str(meal_2["nutrients"]["calories"]))
    p2 = Decimal(str(meal_2["nutrients"]["protein_g"]))

    # Verify doubling
    assert c2 == c1 * Decimal("2")
    assert p2 == p1 * Decimal("2")


# ---------------------------------------------------------------------------
# AC-80 & AC-81: Unit-Aware Grocery List with Dates and Categorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_80_ac_81_grocery_list_date_range_and_grouping(seeded_sub_client):
    client, session, user, goal, plan_data = seeded_sub_client

    plan_id = plan_data["id"]
    day_dates = [d["plan_date"] for d in plan_data["days"]]
    d2 = day_dates[1]
    d4 = day_dates[3]

    # AC-80: Grocery list for days 2 to 4 includes only those days' meals
    resp = await client.get(
        f"/api/meal-plans/{plan_id}/grocery-list",
        params={"from_date": d2, "to_date": d4},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) > 0

    # AC-80: Empty selection returns empty list with 200
    resp_empty = await client.get(
        f"/api/meal-plans/{plan_id}/grocery-list",
        params={"from_date": "2030-01-01", "to_date": "2030-01-02"},
    )
    assert resp_empty.status_code == 200
    assert resp_empty.json()["items"] == []

    # AC-81: Items are grouped by food category and sorted deterministically
    items = data["items"]
    for it in items:
        assert "name" in it
        assert "category" in it
        assert "display_quantity" in it
        assert "unit_family" in it
        assert "is_text_only" in it

    # Check deterministic ordering by category ascending, name ascending
    for i in range(1, len(items)):
        prev = (items[i - 1]["category"], items[i - 1]["name"].lower())
        curr = (items[i]["category"], items[i]["name"].lower())
        assert prev <= curr
