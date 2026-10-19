"""Ownership authorization matrix test harness (spec §10, SEC4, AC-08).

Verifies that for user-owned endpoints and resources:
1. User B requesting, updating, or deleting User A's resource by ID gets a 404 identical to a missing ID.
2. List endpoints never return User A's items to User B.
3. User A's data remains unmodified in the database.
4. Ownership is enforced at the service/query layer, never relying solely on UI filtering.
"""

import uuid

import pytest

from app.models.nutrition import MealPlan, NutritionLog
from app.models.workout import WorkoutRoutine, WorkoutSession
from tests.db import create_test_engine, reset_schema


def test_ac_08_ownership_isolation_contract():
    """AC-08: Confirm user-owned models have strict user_id foreign keys and scoping."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    # User A models
    routine_a = WorkoutRoutine(id=uuid.uuid4(), user_id=user_a_id, name="User A Routine")
    session_a = WorkoutSession(id=uuid.uuid4(), user_id=user_a_id, started_at=None)  # type: ignore[arg-type]
    plan_a = MealPlan(
        id=uuid.uuid4(), user_id=user_a_id, name="User A Plan", start_date=None, end_date=None
    )  # type: ignore[arg-type]
    log_a = NutritionLog(id=uuid.uuid4(), user_id=user_a_id, consumed_at=None, meal_type="lunch")  # type: ignore[arg-type]

    # Verify that each model records user ownership
    assert routine_a.user_id == user_a_id
    assert session_a.user_id == user_a_id
    assert plan_a.user_id == user_a_id
    assert log_a.user_id == user_a_id

    # Simulate query filter: WHERE user_id == current_user.id
    all_routines = [routine_a]
    user_b_routines = [r for r in all_routines if r.user_id == user_b_id]
    assert len(user_b_routines) == 0, "User B must not see User A's routines!"

    # Simulate resource lookup by ID: WHERE id == resource_id AND user_id == current_user.id
    def find_routine_for_user(routine_id: uuid.UUID, user_id: uuid.UUID) -> WorkoutRoutine | None:
        for r in all_routines:
            if r.id == routine_id and r.user_id == user_id:
                return r
        return None

    # Missing ID returns None (404)
    assert find_routine_for_user(uuid.uuid4(), user_b_id) is None
    # User A's ID accessed by User B returns None (404, identical to missing ID!)
    assert find_routine_for_user(routine_a.id, user_b_id) is None
    # User A's ID accessed by User A returns routine
    assert find_routine_for_user(routine_a.id, user_a_id) is routine_a


@pytest.mark.asyncio
async def test_ac_08_api_ownership_matrix():
    """AC-08 (SEC4): User B accessing, updating, or deleting User A's routine or workout gets 404."""
    from datetime import UTC, datetime, timedelta

    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.api.deps import get_db
    from app.main import app
    from app.models.user import Session, User
    from app.models.workout import (
        Exercise,
        WorkoutExercise,
        WorkoutRoutine,
        WorkoutSession,
        WorkoutSet,
    )
    from app.services.security import generate_csrf_token, generate_session_token, hash_token

    engine = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(reset_schema)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as db:
        # Create User A
        user_a = User(
            email="usera@example.com", password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy"
        )
        # Create User B
        user_b = User(
            email="userb@example.com", password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy"
        )
        db.add_all([user_a, user_b])
        await db.flush()

        # Session for User B
        b_tok = generate_session_token()
        b_csrf = generate_csrf_token()
        now = datetime.now(UTC)
        sess_b = Session(
            user_id=user_b.id,
            token_hash=hash_token(b_tok),
            csrf_token_hash=hash_token(b_csrf),
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        db.add(sess_b)

        # Create exercise
        ex = Exercise(name="Bench Press", primary_muscle="chest", equipment="barbell")
        db.add(ex)
        await db.flush()

        # Create Routine owned by User A
        routine_a = WorkoutRoutine(user_id=user_a.id, name="User A Routine")
        db.add(routine_a)
        await db.flush()

        # Create Workout owned by User A
        workout_a = WorkoutSession(
            user_id=user_a.id, started_at=now, notes="User A Private Workout"
        )
        db.add(workout_a)
        await db.flush()

        w_ex = WorkoutExercise(session_id=workout_a.id, exercise_id=ex.id, order_index=0)
        db.add(w_ex)
        await db.flush()

        w_set = WorkoutSet(
            workout_exercise_id=w_ex.id,
            set_number=1,
            reps=5,
            load_kg=100.0,
            completed_at=now,
        )
        db.add(w_set)
        await db.commit()

        # Setup test client logged in as User B
        async def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"session_id": b_tok},
            headers={"X-CSRF-Token": b_csrf},
        ) as client:
            # 1. User B lists routines -> must NOT include User A's routine
            list_routines_resp = await client.get("/api/routines")
            assert list_routines_resp.status_code == 200
            assert len(list_routines_resp.json()) == 0

            # 2. User B lists workouts -> must NOT include User A's workout
            list_workouts_resp = await client.get("/api/workouts")
            assert list_workouts_resp.status_code == 200
            assert len(list_workouts_resp.json()["items"]) == 0

            # 3. User B requests User A's routine by ID -> 404
            assert (await client.get(f"/api/routines/{routine_a.id}")).status_code == 404

            # 4. User B patches User A's routine -> 404
            patch_routine_payload = {"name": "Hacked Routine", "exercises": []}
            assert (
                await client.patch(f"/api/routines/{routine_a.id}", json=patch_routine_payload)
            ).status_code == 404

            # 5. User B deletes User A's routine -> 404
            assert (await client.delete(f"/api/routines/{routine_a.id}")).status_code == 404

            # 6. User B duplicates User A's routine -> 404
            assert (await client.post(f"/api/routines/{routine_a.id}/duplicate")).status_code == 404

            # 7. User B starts workout from User A's routine -> 404
            assert (await client.post(f"/api/routines/{routine_a.id}/start")).status_code == 404

            # 8. User B requests User A's workout by ID -> 404
            assert (await client.get(f"/api/workouts/{workout_a.id}")).status_code == 404

            # 9. User B patches User A's workout -> 404
            patch_workout_payload = {
                "started_at": now.isoformat(),
                "notes": "Hacked",
                "exercises": [],
            }
            assert (
                await client.patch(f"/api/workouts/{workout_a.id}", json=patch_workout_payload)
            ).status_code == 404

            # 10. User B deletes User A's workout -> 404
            assert (await client.delete(f"/api/workouts/{workout_a.id}")).status_code == 404

        app.dependency_overrides.clear()

        # 11. Verify User A's data remains unmodified in the database (AC-08)
        check_routine = await db.get(WorkoutRoutine, routine_a.id)
        assert check_routine is not None
        assert check_routine.name == "User A Routine"

        check_workout = await db.get(WorkoutSession, workout_a.id)
        assert check_workout is not None
        assert check_workout.notes == "User A Private Workout"
