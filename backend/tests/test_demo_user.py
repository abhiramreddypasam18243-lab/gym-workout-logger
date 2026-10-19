"""Tests for Synthetic Demo Account Generator (D4, AC-106)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.demo_user import DEMO_EMAIL, create_demo_user
from app.models.nutrition import (
    FoodNutrient,
    MealPlan,
    NutritionLog,
    NutritionLogItem,
    PlannedMeal,
    PlannedMealItem,
)
from app.models.user import User, UserProfile
from app.models.workout import WorkoutSession
from tests.db import create_test_engine, reset_schema


@pytest.mark.asyncio
async def test_ac_106_create_synthetic_demo_account():
    """AC-106: The demo-user command works, the demo account is labelled synthetic,

    and creates the expected workout history, sets, routines and meal plans.
    """
    engine = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(reset_schema)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Run in quick mode for rapid test execution (60 sessions, 240 sets)
        stats = await create_demo_user(session, num_sessions=60, quick_mode=True)

        assert stats["sessions"] == 60
        assert stats["sets"] == 960  # 60 sessions * 4 exercises * 4 sets
        assert stats["meal_plans"] == 1
        assert stats["planned_meals"] == 28  # 7 days * 4 slots
        assert stats["nutrition_logs"] == 42  # 14 days * 3 meals

        # Verify demo user exists in database
        user_res = await session.execute(select(User).where(User.email == DEMO_EMAIL))
        user = user_res.scalar_one_or_none()
        assert user is not None

        # Verify profile is labelled synthetic (AC-106)
        profile_res = await session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = profile_res.scalar_one_or_none()
        assert profile is not None
        assert "Synthetic" in profile.display_name
        assert profile.adult_confirmed_at is not None

        # Verify workout sessions exist
        sessions_res = await session.execute(
            select(WorkoutSession).where(WorkoutSession.user_id == user.id)
        )
        sessions = list(sessions_res.scalars().all())
        assert len(sessions) == 60
        for s in sessions:
            assert "Synthetic" in (s.notes or "")

        # Demo nutrition values come from the reviewed catalogue, never invented (ag.md)
        plan = (
            await session.execute(select(MealPlan).where(MealPlan.user_id == user.id))
        ).scalar_one()
        items = (
            await session.execute(
                select(PlannedMealItem)
                .join(PlannedMeal, PlannedMealItem.planned_meal_id == PlannedMeal.id)
                .where(PlannedMeal.meal_plan_id == plan.id)
            )
        ).scalars().all()
        assert items
        for item in items:
            if item.food_id is None:
                assert item.nutrient_snapshot == {}  # text-only ingredient
                continue
            rows = (
                await session.execute(select(FoodNutrient).where(FoodNutrient.food_id == item.food_id))
            ).scalars().all()
            assert item.nutrient_snapshot == {r.nutrient_code: str(r.amount_per_100g) for r in rows}

        log_items = (
            await session.execute(
                select(NutritionLogItem)
                .join(NutritionLog, NutritionLogItem.nutrition_log_id == NutritionLog.id)
                .where(NutritionLog.user_id == user.id)
            )
        ).scalars().all()
        assert len(log_items) == 42
        assert all(li.recipe_id is not None for li in log_items)
        assert all(li.nutrient_snapshot["is_recipe_per_serving"] == "true" for li in log_items)

    await engine.dispose()
