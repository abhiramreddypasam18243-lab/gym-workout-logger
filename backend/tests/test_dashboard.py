"""Tests for combined dashboard and non-causal insights (spec §5.9, FR-13, AC-85–87, Rule S8)."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_db
from app.domain.insights import verify_non_causal_wording
from app.main import app
from app.models.user import Session, User, UserProfile
from app.models.workout import Exercise, WorkoutExercise, WorkoutSession, WorkoutSet
from app.services.security import generate_csrf_token, generate_session_token, hash_token
from tests.db import create_test_engine, reset_schema


@pytest.fixture
async def seeded_dashboard_client():
    """Setup test database with user, exercises, and workouts."""
    engine = create_test_engine()
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(reset_schema)

    async with async_session() as session:
        # 1. Create user
        user = User(
            email=f"dashuser_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="argon2id$hashed",
        )
        session.add(user)
        await session.flush()

        profile = UserProfile(
            user_id=user.id,
            display_name="Dashboard User",
            timezone="UTC",
            adult_confirmed_at=datetime.now(UTC),
            birth_date=date(1995, 2, 10),
            nutrition_paused=False,
            calories_hidden=False,
        )
        session.add(profile)

        # 2. Add bench press exercise
        bench = Exercise(
            name="Barbell Bench Press",
            movement_pattern="horizontal_push",
            primary_muscle="chest",
            equipment="barbell",
        )
        session.add(bench)
        await session.flush()

        # 3. Create session tokens
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
            yield client, session, user, bench

        app.dependency_overrides.clear()
    await engine.dispose()


# ---------------------------------------------------------------------------
# AC-85: Combined Dashboard & Empty States for New User
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_85_dashboard_metrics_and_new_user_empty_states(seeded_dashboard_client):
    """AC-85: Dashboard returns weekly sessions, weekly volume, PR count and planned vs logged summaries.

    A new user gets zero values and empty states with status 200.
    """
    client, session, user, bench = seeded_dashboard_client

    # 1. New user check: zero values, empty states, 200 OK
    res_empty = await client.get("/api/dashboard")
    assert res_empty.status_code == 200
    data_empty = res_empty.json()

    assert data_empty["weekly_sessions"] == 0
    assert Decimal(str(data_empty["weekly_volume_kg"])) == Decimal("0")
    assert data_empty["pr_count"] == 0
    assert data_empty["active_plan_id"] is None
    assert "disclaimer" in data_empty

    # 2. Add completed workout sessions in current week
    now = datetime.now(UTC)
    w1 = WorkoutSession(user_id=user.id, started_at=now, completed_at=now + timedelta(minutes=45))
    session.add(w1)
    await session.flush()

    we1 = WorkoutExercise(session_id=w1.id, exercise_id=bench.id, order_index=1)
    session.add(we1)
    await session.flush()

    # Add sets: 80kg x 5 = 400kg, 80kg x 5 = 400kg, warmup 40kg x 10 (excluded from volume)
    session.add_all([
        WorkoutSet(workout_exercise_id=we1.id, set_number=1, reps=10, load_kg=Decimal("40.0"), is_warmup=True, completed_at=now),
        WorkoutSet(workout_exercise_id=we1.id, set_number=2, reps=5, load_kg=Decimal("80.0"), is_warmup=False, completed_at=now),
        WorkoutSet(workout_exercise_id=we1.id, set_number=3, reps=5, load_kg=Decimal("80.0"), is_warmup=False, completed_at=now),
    ])
    await session.commit()

    # Re-query dashboard: weekly_sessions = 1, volume = 800kg
    res_active = await client.get("/api/dashboard")
    assert res_active.status_code == 200
    data_active = res_active.json()

    assert data_active["weekly_sessions"] == 1
    assert Decimal(str(data_active["weekly_volume_kg"])) == Decimal("800")
    # First working set is the baseline and an equal set is not a PR (AC-41) -> 0 PRs
    assert data_active["pr_count"] == 0

    # A heavier set later this week beats the 80 kg x 5 baseline -> 1 PR
    later = now + timedelta(minutes=30)
    session.add(WorkoutSet(workout_exercise_id=we1.id, set_number=4, reps=5, load_kg=Decimal("85.0"), is_warmup=False, completed_at=later))
    await session.commit()
    assert (await client.get("/api/dashboard")).json()["pr_count"] == 1


# ---------------------------------------------------------------------------
# AC-86: Insights Minimum Sessions Threshold (Fewer than 3 Sessions)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_86_insights_minimum_sessions_threshold(seeded_dashboard_client):
    """AC-86: With fewer than 3 sessions of an exercise in the window, no trend insight is produced

    and the response says there is not enough data. Every insight carries window, n, limitations, evidence.
    """
    client, session, user, bench = seeded_dashboard_client

    # 1. 0 sessions -> not enough data
    res_0 = await client.get("/api/insights", params={"exercise_id": str(bench.id)})
    assert res_0.status_code == 200
    d0 = res_0.json()
    assert d0["has_enough_data"] is False
    assert "minimum 3 sessions required" in d0["message"]
    assert len(d0["insights"]) == 0

    # 2. Add 2 sessions (still < 3)
    now = datetime.now(UTC)
    for i in range(2):
        w = WorkoutSession(user_id=user.id, started_at=now - timedelta(days=10 - i * 3))
        session.add(w)
        await session.flush()
        we = WorkoutExercise(session_id=w.id, exercise_id=bench.id, order_index=1)
        session.add(we)
        await session.flush()
        session.add(WorkoutSet(workout_exercise_id=we.id, set_number=1, reps=5, load_kg=Decimal("80.0"), is_warmup=False, completed_at=now))
    await session.commit()

    res_2 = await client.get("/api/insights", params={"exercise_id": str(bench.id)})
    assert res_2.status_code == 200
    d2 = res_2.json()
    assert d2["has_enough_data"] is False
    assert "minimum 3 sessions required" in d2["message"]
    assert len(d2["insights"]) == 0

    # 3. Add 3rd session (now >= 3 sessions!)
    w3 = WorkoutSession(user_id=user.id, started_at=now - timedelta(days=1))
    session.add(w3)
    await session.flush()
    we3 = WorkoutExercise(session_id=w3.id, exercise_id=bench.id, order_index=1)
    session.add(we3)
    await session.flush()
    # 90kg x 5 reps -> e1RM = 101.25 kg
    session.add(WorkoutSet(workout_exercise_id=we3.id, set_number=1, reps=5, load_kg=Decimal("90.0"), is_warmup=False, completed_at=now))
    await session.commit()

    res_3 = await client.get("/api/insights", params={"exercise_id": str(bench.id)})
    assert res_3.status_code == 200
    d3 = res_3.json()
    assert d3["has_enough_data"] is True
    assert len(d3["insights"]) >= 1

    # Verify mandatory metadata on every insight (AC-86)
    ins = d3["insights"][0]
    assert "window" in ins
    assert "n" in ins and ins["n"] >= 3
    assert "limitations" in ins and "Observational correlation" in ins["limitations"]
    assert "evidence" in ins
    assert "statement" in ins


# ---------------------------------------------------------------------------
# AC-87: Non-Causal Wording Rule (Rule S8)
# ---------------------------------------------------------------------------


def test_ac_87_non_causal_wording_verification():
    """AC-87: Insight templates contain no causal wording (verified with banned-word test)."""
    # Test that verify_non_causal_wording catches all prohibited causal words
    banned_samples = [
        "Your training caused a 5kg gain.",
        "Your e1RM increased because of protein intake.",
        "Higher volume led to faster recovery.",
        "This program optimizes muscle hypertrophy.",
        "Creatine boosts bench press performance.",
        "Skipping meals results in lower energy.",
        "This proves that high protein enhances strength.",
    ]

    for sample in banned_samples:
        with pytest.raises(ValueError):
            verify_non_causal_wording(sample)

    # Descriptive, observational sentences must pass
    valid_samples = [
        "During the last 4 weeks across 4 logged sessions, estimated 1RM differed by +5.0 kg.",
        "Days with logged protein intake at or above target coincided with an average session volume of 1200 kg.",
        "Estimated 1RM was observed to be higher during weeks with 4 logged sessions.",
    ]
    for valid in valid_samples:
        verify_non_causal_wording(valid)
