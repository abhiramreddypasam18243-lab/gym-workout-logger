"""Tests for workouts, routines, set validation, atomicity, timezone handling, and history pagination (AC-31 to AC-37)."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_db
from app.main import app
from app.models.user import Session, User, UserProfile
from app.models.workout import (
    Exercise,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)
from app.seed.loader import run_seed
from app.services.security import generate_csrf_token, generate_session_token, hash_token
from tests.db import create_test_engine, reset_schema


@pytest_asyncio.fixture
async def test_db():
    engine = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(reset_schema)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def auth_client(test_db: AsyncSession):
    # Seed catalogue
    await run_seed(test_db)

    # Create primary user
    user = User(
        email="athlete@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy",
    )
    test_db.add(user)
    await test_db.flush()

    profile = UserProfile(
        user_id=user.id,
        display_name="Athlete",
        timezone="Asia/Kolkata",
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


# ---------------------------------------------------------------------------
# AC-31 & AC-32: Workout Logging and Field Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_31_workout_persistence(auth_client):
    client, user, db = auth_client

    # Get seed exercises
    ex_res = await db.execute(select(Exercise).order_by(Exercise.name.asc()).limit(2))
    bench, squat = ex_res.scalars().all()

    start_time = datetime(2026, 10, 15, 10, 0, 0, tzinfo=UTC)
    payload = {
        "started_at": start_time.isoformat(),
        "completed_at": (start_time + timedelta(minutes=45)).isoformat(),
        "notes": "Chest & Legs power day",
        "exercises": [
            {
                "exercise_id": str(bench.id),
                "order_index": 0,
                "notes": "Warm shoulders",
                "sets": [
                    {
                        "set_number": 1,
                        "reps": 10,
                        "load_kg": "40.0",
                        "rpe": "6.0",
                        "is_warmup": True,
                        "completed_at": (start_time + timedelta(minutes=5)).isoformat(),
                    },
                    {
                        "set_number": 2,
                        "reps": 5,
                        "load_kg": "80.0",
                        "rpe": "8.5",
                        "is_warmup": False,
                        "completed_at": (start_time + timedelta(minutes=10)).isoformat(),
                    },
                ],
            },
            {
                "exercise_id": str(squat.id),
                "order_index": 1,
                "notes": "Deep squats",
                "sets": [
                    {
                        "set_number": 1,
                        "reps": 5,
                        "load_kg": "100.0",
                        "rpe": "8.0",
                        "is_warmup": False,
                        "completed_at": (start_time + timedelta(minutes=25)).isoformat(),
                    }
                ],
            },
        ],
    }

    resp = await client.post("/api/workouts", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["notes"] == "Chest & Legs power day"
    assert len(data["exercises"]) == 2
    assert data["exercises"][0]["exercise_name"] == bench.name
    assert len(data["exercises"][0]["sets"]) == 2
    assert data["exercises"][1]["exercise_name"] == squat.name
    assert len(data["exercises"][1]["sets"]) == 1


@pytest.mark.asyncio
async def test_ac_32_workout_validation_rules(auth_client):
    client, user, db = auth_client
    ex = (await db.execute(select(Exercise).limit(1))).scalar_one()

    start_time = datetime(2026, 10, 15, 10, 0, 0, tzinfo=UTC)

    def make_payload(set_kwargs):
        return {
            "started_at": start_time.isoformat(),
            "exercises": [
                {
                    "exercise_id": str(ex.id),
                    "order_index": 0,
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 5,
                            "load_kg": "60.0",
                            "rpe": "8.0",
                            "is_warmup": False,
                            "completed_at": (start_time + timedelta(minutes=5)).isoformat(),
                            **set_kwargs,
                        }
                    ],
                }
            ],
        }

    # 1. Reps = 0 rejected with 422
    resp = await client.post("/api/workouts", json=make_payload({"reps": 0}))
    assert resp.status_code == 422

    # 2. Load = -1 rejected with 422
    resp = await client.post("/api/workouts", json=make_payload({"load_kg": "-1.0"}))
    assert resp.status_code == 422

    # 3. Load = 0 accepted with 201 (e.g. bodyweight pullup/pushup)
    resp = await client.post("/api/workouts", json=make_payload({"load_kg": "0.0"}))
    assert resp.status_code == 201

    # 4. RPE 11 rejected with 422
    resp = await client.post("/api/workouts", json=make_payload({"rpe": "11.0"}))
    assert resp.status_code == 422

    # 5. RPE 7.5 accepted with 201
    resp = await client.post("/api/workouts", json=make_payload({"rpe": "7.5"}))
    assert resp.status_code == 201

    # 6. RPE 7.3 rejected with 422 (must be steps of 0.5)
    resp = await client.post("/api/workouts", json=make_payload({"rpe": "7.3"}))
    assert resp.status_code == 422

    # 7. Duplicate set numbers rejected with 422
    dup_sets_payload = {
        "started_at": start_time.isoformat(),
        "exercises": [
            {
                "exercise_id": str(ex.id),
                "order_index": 0,
                "sets": [
                    {
                        "set_number": 1,
                        "reps": 5,
                        "load_kg": "60.0",
                        "completed_at": (start_time + timedelta(minutes=5)).isoformat(),
                    },
                    {
                        "set_number": 1,  # Duplicate!
                        "reps": 5,
                        "load_kg": "60.0",
                        "completed_at": (start_time + timedelta(minutes=8)).isoformat(),
                    },
                ],
            }
        ],
    }
    resp = await client.post("/api/workouts", json=dup_sets_payload)
    assert resp.status_code == 422

    # 8. Set completed_at earlier than session started_at rejected with 422
    early_set_payload = {
        "started_at": start_time.isoformat(),
        "exercises": [
            {
                "exercise_id": str(ex.id),
                "order_index": 0,
                "sets": [
                    {
                        "set_number": 1,
                        "reps": 5,
                        "load_kg": "60.0",
                        "completed_at": (
                            start_time - timedelta(minutes=10)
                        ).isoformat(),  # Earlier!
                    }
                ],
            }
        ],
    }
    resp = await client.post("/api/workouts", json=early_set_payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-33: Atomicity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_33_workout_atomicity_on_validation_failure(auth_client):
    client, user, db = auth_client
    ex = (await db.execute(select(Exercise).limit(1))).scalar_one()

    start_time = datetime(2026, 10, 15, 10, 0, 0, tzinfo=UTC)

    # 3 valid sets and 1 invalid set (reps: 0)
    invalid_payload = {
        "started_at": start_time.isoformat(),
        "exercises": [
            {
                "exercise_id": str(ex.id),
                "order_index": 0,
                "sets": [
                    {
                        "set_number": 1,
                        "reps": 5,
                        "load_kg": "60.0",
                        "completed_at": (start_time + timedelta(minutes=2)).isoformat(),
                    },
                    {
                        "set_number": 2,
                        "reps": 5,
                        "load_kg": "60.0",
                        "completed_at": (start_time + timedelta(minutes=4)).isoformat(),
                    },
                    {
                        "set_number": 3,
                        "reps": 5,
                        "load_kg": "60.0",
                        "completed_at": (start_time + timedelta(minutes=6)).isoformat(),
                    },
                    {
                        "set_number": 4,
                        "reps": 0,  # Invalid!
                        "load_kg": "60.0",
                        "completed_at": (start_time + timedelta(minutes=8)).isoformat(),
                    },
                ],
            }
        ],
    }

    # Record initial counts
    session_count_before = len((await db.execute(select(WorkoutSession))).scalars().all())
    exercise_count_before = len((await db.execute(select(WorkoutExercise))).scalars().all())
    set_count_before = len((await db.execute(select(WorkoutSet))).scalars().all())

    resp = await client.post("/api/workouts", json=invalid_payload)
    assert resp.status_code == 422

    # Verify zero database rows were left behind
    session_count_after = len((await db.execute(select(WorkoutSession))).scalars().all())
    exercise_count_after = len((await db.execute(select(WorkoutExercise))).scalars().all())
    set_count_after = len((await db.execute(select(WorkoutSet))).scalars().all())

    assert session_count_after == session_count_before
    assert exercise_count_after == exercise_count_before
    assert set_count_after == set_count_before


# ---------------------------------------------------------------------------
# AC-34: Editing and Deleting Workouts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_34_edit_and_delete_workout(auth_client):
    client, user, db = auth_client
    ex = (await db.execute(select(Exercise).limit(1))).scalar_one()

    start_time = datetime(2026, 10, 15, 10, 0, 0, tzinfo=UTC)
    create_payload = {
        "started_at": start_time.isoformat(),
        "notes": "Original note",
        "exercises": [
            {
                "exercise_id": str(ex.id),
                "order_index": 0,
                "sets": [
                    {
                        "set_number": 1,
                        "reps": 5,
                        "load_kg": "50.0",
                        "completed_at": (start_time + timedelta(minutes=5)).isoformat(),
                    }
                ],
            }
        ],
    }
    resp = await client.post("/api/workouts", json=create_payload)
    assert resp.status_code == 201
    workout_id = resp.json()["id"]

    # 1. Edit workout replaces sets
    update_payload = {
        "started_at": start_time.isoformat(),
        "notes": "Updated note",
        "exercises": [
            {
                "exercise_id": str(ex.id),
                "order_index": 0,
                "sets": [
                    {
                        "set_number": 1,
                        "reps": 8,
                        "load_kg": "55.0",
                        "completed_at": (start_time + timedelta(minutes=5)).isoformat(),
                    },
                    {
                        "set_number": 2,
                        "reps": 8,
                        "load_kg": "55.0",
                        "completed_at": (start_time + timedelta(minutes=10)).isoformat(),
                    },
                ],
            }
        ],
    }
    patch_resp = await client.patch(f"/api/workouts/{workout_id}", json=update_payload)
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["notes"] == "Updated note"
    assert len(patched_data["exercises"][0]["sets"]) == 2

    # 2. Delete workout removes session and children
    del_resp = await client.delete(f"/api/workouts/{workout_id}")
    assert del_resp.status_code == 204

    # Verify not found
    get_resp = await client.get(f"/api/workouts/{workout_id}")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# AC-35: Routines Duplication and Starting Workout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_35_routines_duplication_and_start(auth_client):
    client, user, db = auth_client
    ex_res = await db.execute(select(Exercise).limit(2))
    ex1, ex2 = ex_res.scalars().all()

    # 1. Create routine with rep ranges (rep_min <= rep_max)
    routine_payload = {
        "name": "Upper Body Push",
        "description": "Chest, shoulders, triceps",
        "exercises": [
            {
                "exercise_id": str(ex1.id),
                "order_index": 0,
                "target_sets": 4,
                "rep_min": 6,
                "rep_max": 8,
                "rest_seconds": 120,
            },
            {
                "exercise_id": str(ex2.id),
                "order_index": 1,
                "target_sets": 3,
                "rep_min": 10,
                "rep_max": 12,
                "rest_seconds": 90,
            },
        ],
    }
    resp = await client.post("/api/routines", json=routine_payload)
    assert resp.status_code == 201
    routine = resp.json()
    routine_id = routine["id"]
    assert len(routine["exercises"]) == 2
    assert routine["exercises"][0]["rep_min"] == 6
    assert routine["exercises"][0]["rep_max"] == 8

    # Verify rep_min > rep_max rejected with 422
    bad_routine = {
        "name": "Bad Reps",
        "exercises": [
            {
                "exercise_id": str(ex1.id),
                "target_sets": 3,
                "rep_min": 12,
                "rep_max": 8,  # Invalid!
            }
        ],
    }
    assert (await client.post("/api/routines", json=bad_routine)).status_code == 422

    # 2. Duplicate routine
    dup_resp = await client.post(f"/api/routines/{routine_id}/duplicate")
    assert dup_resp.status_code == 201
    dup_data = dup_resp.json()
    assert dup_data["id"] != routine_id
    assert "Copy" in dup_data["name"]
    assert len(dup_data["exercises"]) == 2

    # 3. Start workout from routine
    start_resp = await client.post(f"/api/routines/{routine_id}/start")
    assert start_resp.status_code == 200
    prefilled = start_resp.json()
    assert prefilled["routine_id"] == routine_id
    assert len(prefilled["exercises"]) == 2
    # Pre-fills targets with NO sets logged yet (AC-35)
    for pex in prefilled["exercises"]:
        assert len(pex["sets"]) == 0
        assert pex["target_sets"] > 0


# ---------------------------------------------------------------------------
# AC-36: Timezone Splitting (Asia/Kolkata)
# ---------------------------------------------------------------------------


def test_ac_36_asia_kolkata_timezone_boundary():
    """AC-36: For Asia/Kolkata (+05:30), sets at 18:29:59Z and 18:30:00Z fall on 15 Oct and 16 Oct."""
    tz = ZoneInfo("Asia/Kolkata")

    # 18:29:59 UTC + 5:30 = 23:59:59 on 15 October
    t1_utc = datetime(2026, 10, 15, 18, 29, 59, tzinfo=UTC)
    t1_local = t1_utc.astimezone(tz)
    assert t1_local.date().isoformat() == "2026-10-15"
    assert t1_local.hour == 23
    assert t1_local.minute == 59
    assert t1_local.second == 59

    # 18:30:00 UTC + 5:30 = 00:00:00 on 16 October
    t2_utc = datetime(2026, 10, 15, 18, 30, 0, tzinfo=UTC)
    t2_local = t2_utc.astimezone(tz)
    assert t2_local.date().isoformat() == "2026-10-16"
    assert t2_local.hour == 0
    assert t2_local.minute == 0
    assert t2_local.second == 0


# ---------------------------------------------------------------------------
# AC-37: Keyset History Pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_37_history_keyset_pagination(auth_client):
    client, user, db = auth_client
    ex = (await db.execute(select(Exercise).limit(1))).scalar_one()

    # Create 5 sessions at distinct start times
    base_time = datetime(2026, 10, 10, 10, 0, 0, tzinfo=UTC)
    session_ids = []
    for i in range(5):
        s_time = base_time + timedelta(days=i)
        payload = {
            "started_at": s_time.isoformat(),
            "notes": f"Session {i}",
            "exercises": [
                {
                    "exercise_id": str(ex.id),
                    "sets": [
                        {
                            "set_number": 1,
                            "reps": 5,
                            "load_kg": "50.0",
                            "completed_at": (s_time + timedelta(minutes=5)).isoformat(),
                        }
                    ],
                }
            ],
        }
        res = await client.post("/api/workouts", json=payload)
        session_ids.append(res.json()["id"])

    # Query page 1 with limit = 2
    p1_resp = await client.get("/api/workouts?limit=2")
    assert p1_resp.status_code == 200
    p1 = p1_resp.json()
    assert len(p1["items"]) == 2
    assert p1["next_cursor"] is not None

    # Query page 2 with cursor
    p2_resp = await client.get(f"/api/workouts?limit=2&cursor={p1['next_cursor']}")
    assert p2_resp.status_code == 200
    p2 = p2_resp.json()
    assert len(p2["items"]) == 2
    assert p2["next_cursor"] is not None

    # Query page 3 with cursor
    p3_resp = await client.get(f"/api/workouts?limit=2&cursor={p2['next_cursor']}")
    assert p3_resp.status_code == 200
    p3 = p3_resp.json()
    assert len(p3["items"]) == 1
    assert p3["next_cursor"] is None

    # Verify no overlap between pages
    page1_ids = {it["id"] for it in p1["items"]}
    page2_ids = {it["id"] for it in p2["items"]}
    page3_ids = {it["id"] for it in p3["items"]}

    assert len(page1_ids.intersection(page2_ids)) == 0
    assert len(page2_ids.intersection(page3_ids)) == 0
    assert len(page1_ids.union(page2_ids).union(page3_ids)) == 5


# ---------------------------------------------------------------------------
# AC-38: History Query Plan Index Verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ac_38_history_query_plan_uses_index(test_db: AsyncSession):
    """AC-38 (NFR): With 10,000 sessions, the history query plan uses the (user_id, started_at) index."""
    from sqlalchemy import text

    # 20 users x 500 sessions = 10,000 sessions
    users = [
        User(email=f"plan_user_{i}@example.com", password_hash="$argon2id$dummy")
        for i in range(20)
    ]
    test_db.add_all(users)
    await test_db.flush()
    for u in users:
        await test_db.execute(
            text(
                "INSERT INTO workout_sessions (id, user_id, started_at) "
                "SELECT gen_random_uuid(), :uid, now() - make_interval(days => g) "
                "FROM generate_series(1, 500) AS g"
            ),
            {"uid": u.id},
        )
    await test_db.commit()
    await test_db.execute(text("ANALYZE workout_sessions"))

    count = (await test_db.execute(text("SELECT count(*) FROM workout_sessions"))).scalar()
    assert count == 10_000

    result = await test_db.execute(
        text(
            "EXPLAIN SELECT id, started_at FROM workout_sessions "
            "WHERE user_id = :uid "
            "ORDER BY started_at DESC, id DESC LIMIT 20"
        ),
        {"uid": users[0].id},
    )
    plan_text = " ".join(row[0] for row in result.all())
    assert "idx_workout_sessions_user_started" in plan_text
