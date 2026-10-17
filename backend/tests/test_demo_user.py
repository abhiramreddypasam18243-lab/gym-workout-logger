"""Tests for Synthetic Demo Account Generator (D4, AC-106)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.demo_user import DEMO_EMAIL, create_demo_user
from app.models.base import Base
from app.models.user import User, UserProfile
from app.models.workout import WorkoutSession


@pytest.mark.asyncio
async def test_ac_106_create_synthetic_demo_account():
    """AC-106: The demo-user command works, the demo account is labelled synthetic,

    and creates the expected workout history, sets, routines and meal plans.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

    await engine.dispose()
