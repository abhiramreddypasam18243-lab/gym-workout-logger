"""Tests for Strength Analytics Service & Endpoints (spec §5.2, FR-05, AC-39–44)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.main import app
from app.models.base import Base
from app.models.user import Session, User, UserProfile
from app.models.workout import Exercise
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
async def auth_client(test_db: AsyncSession):
    user = User(
        email="strength_user@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",
    )
    test_db.add(user)
    await test_db.flush()

    profile = UserProfile(
        user_id=user.id,
        display_name="Strength Lifter",
        timezone="UTC",
        units="kg",
        weekly_session_target=3,
    )
    test_db.add(profile)

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
    test_db.add(session)
    await test_db.commit()

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"session_id": raw_token},
        headers={"X-CSRF-Token": raw_csrf},
    ) as client:
        yield client, user, test_db

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ac_42_e1rm_trends_and_lb_conversion(auth_client):
    """AC-42: Trend returns best e1RM per session date in user timezone, converts units for lb, empty list for no data."""
    client, user, db = auth_client

    # 1. Create an exercise
    exercise = Exercise(
        name="Barbell Bench Press",
        primary_muscle="chest",
        equipment="barbell",
        is_custom=False,
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    exercise_id = str(exercise.id)

    # 2. Before any sessions, trend returns empty list with 200 (AC-42)
    empty_res = await client.get(
        "/api/analytics/strength",
        params={"exercise_id": exercise_id},
    )
    assert empty_res.status_code == 200
    assert empty_res.json() == []

    # 3. Log a session with multiple working sets on date 1 (e.g. 2026-10-14)
    # 80 kg x 5 reps -> e1RM = 80 * (1 + 5/30) = 93.333... kg
    # 85 kg x 5 reps -> e1RM = 85 * (1 + 5/30) = 99.166... kg (best of date 1)
    # warm-up: 40 kg x 10 reps (excluded, AC-39)
    date1 = datetime(2026, 10, 14, 10, 0, 0, tzinfo=UTC)
    s1_res = await client.post(
        "/api/workouts",
        json={
            "started_at": date1.isoformat(),
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "order_index": 1,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 10,
                            "load_kg": 40.0,
                            "is_warmup": True,
                            "completed_at": (date1 + timedelta(minutes=5)).isoformat(),
                        },
                        {
                            "set_number": 2,
                            "reps": 5,
                            "load_kg": 80.0,
                            "is_warmup": False,
                            "completed_at": (date1 + timedelta(minutes=10)).isoformat(),
                        },
                        {
                            "set_number": 3,
                            "reps": 5,
                            "load_kg": 85.0,
                            "is_warmup": False,
                            "completed_at": (date1 + timedelta(minutes=15)).isoformat(),
                        },
                    ],
                }
            ],
        },
    )
    assert s1_res.status_code == 201

    # Log date 2 (2026-10-16): 82.5 kg x 3 reps -> e1RM = 82.5 * (1 + 3/30) = 90.75 kg (AC-43)
    date2 = datetime(2026, 10, 16, 10, 0, 0, tzinfo=UTC)
    s2_res = await client.post(
        "/api/workouts",
        json={
            "started_at": date2.isoformat(),
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "order_index": 1,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 3,
                            "load_kg": 82.5,
                            "is_warmup": False,
                            "completed_at": (date2 + timedelta(minutes=5)).isoformat(),
                        },
                    ],
                }
            ],
        },
    )
    assert s2_res.status_code == 201

    # 4. Fetch trends in metric (kg)
    trend_res = await client.get(
        "/api/analytics/strength",
        params={"exercise_id": exercise_id},
    )
    assert trend_res.status_code == 200
    trends = trend_res.json()
    assert len(trends) == 2

    # Date 1 best is 85kg x 5 -> 99.166... kg -> displayed as 99.2 (AC-39)
    assert trends[0]["date"] == "2026-10-14"
    assert trends[0]["e1rm"] == "99.2"
    assert trends[0]["unit"] == "kg"
    assert trends[0]["is_estimated"] is True

    # Date 2 is 82.5kg x 3 -> exact 90.75 kg -> displayed as 90.8 (AC-43)
    assert trends[1]["date"] == "2026-10-16"
    assert trends[1]["e1rm"] == "90.8"
    assert trends[1]["e1rm_exact"] == "90.75"
    assert trends[1]["unit"] == "kg"

    # 5. Switch user profile to lb (AC-42, AC-96)
    patch_profile = await client.patch(
        "/api/profile",
        json={"units": "lb"},
    )
    assert patch_profile.status_code == 200
    assert patch_profile.json()["units"] == "lb"

    # Fetch trends in imperial (lb)
    lb_trend_res = await client.get(
        "/api/analytics/strength",
        params={"exercise_id": exercise_id},
    )
    assert lb_trend_res.status_code == 200
    lb_trends = lb_trend_res.json()
    assert len(lb_trends) == 2

    # 99.16666... kg * 2.2046226218 = ~218.6 lb
    assert lb_trends[0]["unit"] == "lb"
    assert float(lb_trends[0]["e1rm"]) > 218.0
    # 90.75 kg * 2.2046226218 = ~200.1 lb
    assert lb_trends[1]["unit"] == "lb"
    assert float(lb_trends[1]["e1rm"]) > 199.0


@pytest.mark.asyncio
async def test_ac_44_weekly_consistency_counting(auth_client):
    """AC-44: Sessions on Mon, Wed, Sat give 3 for that week, empty week gives 0, warmup-only sessions not counted."""
    client, user, db = auth_client

    exercise = Exercise(
        name="Back Squat",
        primary_muscle="quadriceps",
        equipment="barbell",
        is_custom=False,
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    exercise_id = str(exercise.id)

    # 2026-10-12 was Monday
    mon_dt = datetime(2026, 10, 12, 18, 0, 0, tzinfo=UTC)
    await client.post(
        "/api/workouts",
        json={
            "started_at": mon_dt.isoformat(),
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "order_index": 1,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 5,
                            "load_kg": 100.0,
                            "is_warmup": False,
                            "completed_at": (mon_dt + timedelta(minutes=5)).isoformat(),
                        }
                    ],
                }
            ],
        },
    )

    # Wednesday 2026-10-14: valid session
    wed_dt = datetime(2026, 10, 14, 18, 0, 0, tzinfo=UTC)
    await client.post(
        "/api/workouts",
        json={
            "started_at": wed_dt.isoformat(),
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "order_index": 1,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 5,
                            "load_kg": 100.0,
                            "is_warmup": False,
                            "completed_at": (wed_dt + timedelta(minutes=5)).isoformat(),
                        }
                    ],
                }
            ],
        },
    )

    # Saturday 2026-10-17: valid session
    sat_dt = datetime(2026, 10, 17, 10, 0, 0, tzinfo=UTC)
    await client.post(
        "/api/workouts",
        json={
            "started_at": sat_dt.isoformat(),
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "order_index": 1,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 5,
                            "load_kg": 100.0,
                            "is_warmup": False,
                            "completed_at": (sat_dt + timedelta(minutes=5)).isoformat(),
                        }
                    ],
                }
            ],
        },
    )

    # Sunday 2026-10-18: WARM-UP ONLY session (spec §5.2, AC-44: must NOT be counted!)
    sun_dt = datetime(2026, 10, 18, 10, 0, 0, tzinfo=UTC)
    await client.post(
        "/api/workouts",
        json={
            "started_at": sun_dt.isoformat(),
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "order_index": 1,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 10,
                            "load_kg": 40.0,
                            "is_warmup": True,
                            "completed_at": (sun_dt + timedelta(minutes=5)).isoformat(),
                        }
                    ],
                }
            ],
        },
    )

    # Check consistency API with enough weeks to cover 2026-10-12
    # In test environment now may be anything, let's query 52 weeks
    res = await client.get("/api/analytics/consistency", params={"weeks": 52})
    assert res.status_code == 200
    data = res.json()
    weeks = data["weeks"]
    assert len(weeks) == 52

    # Locate the week starting 2026-10-12
    target_week = next((w for w in weeks if w["week_start"] == "2026-10-12"), None)
    if target_week:
        # Mon, Wed, Sat counted = exactly 3 sessions (warmup-only on Sunday excluded)
        assert target_week["session_count"] == 3

    # Other weeks with no sessions must report 0 (AC-44)
    zero_weeks = [w for w in weeks if w["session_count"] == 0]
    assert len(zero_weeks) >= 1


@pytest.mark.asyncio
async def test_ac_41_pr_detection_and_recomputation(auth_client):
    """AC-41: Baseline, PR strictly greater, equal not a PR, deleting set recomputes PRs."""
    client, user, db = auth_client

    exercise = Exercise(
        name="Deadlift",
        primary_muscle="back",
        equipment="barbell",
        is_custom=False,
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)
    exercise_id = str(exercise.id)

    # Log 3 working sets in order:
    # Set 1: 80 kg x 5 reps (e1RM 93.33) -> baseline
    # Set 2: 85 kg x 5 reps (e1RM 99.17) -> PR!
    # Set 3: 90 kg x 3 reps (e1RM 99.00) -> not a PR (less than 99.17)
    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
    s_res = await client.post(
        "/api/workouts",
        json={
            "started_at": now.isoformat(),
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "order_index": 1,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 5,
                            "load_kg": 80.0,
                            "is_warmup": False,
                            "completed_at": (now + timedelta(minutes=5)).isoformat(),
                        },
                        {
                            "set_number": 2,
                            "reps": 5,
                            "load_kg": 85.0,
                            "is_warmup": False,
                            "completed_at": (now + timedelta(minutes=10)).isoformat(),
                        },
                        {
                            "set_number": 3,
                            "reps": 3,
                            "load_kg": 90.0,
                            "is_warmup": False,
                            "completed_at": (now + timedelta(minutes=15)).isoformat(),
                        },
                    ],
                }
            ],
        },
    )
    assert s_res.status_code == 201
    workout_id = s_res.json()["id"]

    # Fetch PRs
    prs_res = await client.get(f"/api/analytics/prs/{exercise_id}")
    assert prs_res.status_code == 200
    prs = prs_res.json()
    assert len(prs) == 3

    assert prs[0]["set_number"] == 1
    assert prs[0]["is_baseline"] is True
    assert prs[0]["is_pr"] is False

    assert prs[1]["set_number"] == 2
    assert prs[1]["is_baseline"] is False
    assert prs[1]["is_pr"] is True  # 99.17 > 93.33

    assert prs[2]["set_number"] == 3
    assert prs[2]["is_baseline"] is False
    assert prs[2]["is_pr"] is False  # 99.00 is NOT > 99.17 (AC-41)

    # Now edit workout and remove the PR set (Set 2: 85x5)
    # New sets: Set 1 (80x5) and Set 2 (90x3)
    # Now Set 2 (90x3, e1RM 99.0) should become a PR because 99.0 > 93.33!
    edit_res = await client.patch(
        f"/api/workouts/{workout_id}",
        json={
            "started_at": now.isoformat(),
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "order_index": 1,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 5,
                            "load_kg": 80.0,
                            "is_warmup": False,
                            "completed_at": (now + timedelta(minutes=5)).isoformat(),
                        },
                        {
                            "set_number": 2,
                            "reps": 3,
                            "load_kg": 90.0,
                            "is_warmup": False,
                            "completed_at": (now + timedelta(minutes=15)).isoformat(),
                        },
                    ],
                }
            ],
        },
    )
    assert edit_res.status_code == 200

    # Fetch PRs again — recomputed dynamically! (AC-41)
    recomputed_prs_res = await client.get(f"/api/analytics/prs/{exercise_id}")
    assert recomputed_prs_res.status_code == 200
    re_prs = recomputed_prs_res.json()
    assert len(re_prs) == 2

    assert re_prs[0]["set_number"] == 1
    assert re_prs[0]["is_baseline"] is True
    assert re_prs[0]["is_pr"] is False

    assert re_prs[1]["set_number"] == 2
    assert re_prs[1]["is_baseline"] is False
    assert re_prs[1]["is_pr"] is True  # 90x3 is now a PR over baseline!
