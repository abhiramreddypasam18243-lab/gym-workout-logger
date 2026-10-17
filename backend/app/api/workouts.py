"""Workout and routine API endpoints (spec §6, FR-03, FR-04, AC-31–38)."""

import base64
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user_required, get_db, verify_csrf
from app.models.user import User
from app.models.workout import (
    Exercise,
    RoutineExercise,
    WorkoutExercise,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSet,
)
from app.schemas.workout import (
    RoutineCreateRequest,
    RoutineExerciseResponse,
    RoutineResponse,
    WorkoutExerciseResponse,
    WorkoutHistoryResponse,
    WorkoutSessionCreateRequest,
    WorkoutSessionResponse,
    WorkoutSetResponse,
)

router = APIRouter(prefix="/api", tags=["workouts"])


# ---------------------------------------------------------------------------
# Helpers & Mappers
# ---------------------------------------------------------------------------


def _map_routine_to_response(routine: WorkoutRoutine) -> RoutineResponse:
    exercises = [
        RoutineExerciseResponse(
            id=re.id,
            exercise_id=re.exercise_id,
            exercise_name=re.exercise.name if re.exercise else None,
            order_index=re.order_index,
            target_sets=re.target_sets,
            rep_min=re.rep_min,
            rep_max=re.rep_max,
            rest_seconds=re.rest_seconds,
        )
        for re in routine.exercises
    ]
    return RoutineResponse(
        id=routine.id,
        name=routine.name,
        description=routine.description,
        exercises=exercises,
        created_at=routine.created_at,
        updated_at=routine.updated_at,
    )


def _map_session_to_response(session: WorkoutSession) -> WorkoutSessionResponse:
    exercises = [
        WorkoutExerciseResponse(
            id=we.id,
            exercise_id=we.exercise_id,
            exercise_name=we.exercise.name if we.exercise else None,
            order_index=we.order_index,
            notes=we.notes,
            sets=[
                WorkoutSetResponse(
                    id=s.id,
                    set_number=s.set_number,
                    reps=s.reps,
                    load_kg=s.load_kg,
                    rpe=s.rpe,
                    is_warmup=s.is_warmup,
                    completed_at=s.completed_at,
                )
                for s in we.sets
            ],
        )
        for we in session.exercises
    ]
    return WorkoutSessionResponse(
        id=session.id,
        routine_id=session.routine_id,
        started_at=session.started_at,
        completed_at=session.completed_at,
        notes=session.notes,
        exercises=exercises,
    )


# ---------------------------------------------------------------------------
# Routines Endpoints (FR-04, AC-35)
# ---------------------------------------------------------------------------


@router.get("/routines", response_model=list[RoutineResponse])
async def list_routines(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> list[RoutineResponse]:
    """List routines owned by the current user."""
    stmt = (
        select(WorkoutRoutine)
        .options(selectinload(WorkoutRoutine.exercises).selectinload(RoutineExercise.exercise))
        .where(WorkoutRoutine.user_id == current_user.id)
        .order_by(WorkoutRoutine.created_at.desc())
    )
    result = await db.execute(stmt)
    routines = result.scalars().all()
    return [_map_routine_to_response(r) for r in routines]


@router.post("/routines", response_model=RoutineResponse, status_code=status.HTTP_201_CREATED)
async def create_routine(
    payload: RoutineCreateRequest,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> RoutineResponse:
    """Create a new routine template with ordered exercises and rep ranges (AC-35)."""
    routine = WorkoutRoutine(
        user_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(routine)
    await db.flush()

    for ex in payload.exercises:
        re = RoutineExercise(
            routine_id=routine.id,
            exercise_id=ex.exercise_id,
            order_index=ex.order_index,
            target_sets=ex.target_sets,
            rep_min=ex.rep_min,
            rep_max=ex.rep_max,
            rest_seconds=ex.rest_seconds,
        )
        db.add(re)

    await db.commit()
    # Reload with exercises
    reloaded = await db.execute(
        select(WorkoutRoutine)
        .options(selectinload(WorkoutRoutine.exercises).selectinload(RoutineExercise.exercise))
        .where(WorkoutRoutine.id == routine.id)
    )
    return _map_routine_to_response(reloaded.scalar_one())


@router.get("/routines/{routine_id}", response_model=RoutineResponse)
async def get_routine(
    routine_id: uuid.UUID,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> RoutineResponse:
    """Get routine details by ID (enforces ownership, AC-08)."""
    stmt = (
        select(WorkoutRoutine)
        .options(selectinload(WorkoutRoutine.exercises).selectinload(RoutineExercise.exercise))
        .where(
            WorkoutRoutine.id == routine_id,
            WorkoutRoutine.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    routine = result.scalar_one_or_none()
    if not routine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routine_not_found")
    return _map_routine_to_response(routine)


@router.patch("/routines/{routine_id}", response_model=RoutineResponse)
async def update_routine(
    routine_id: uuid.UUID,
    payload: RoutineCreateRequest,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> RoutineResponse:
    """Update routine details and replace exercises (AC-35)."""
    stmt = (
        select(WorkoutRoutine)
        .options(selectinload(WorkoutRoutine.exercises))
        .where(
            WorkoutRoutine.id == routine_id,
            WorkoutRoutine.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    routine = result.scalar_one_or_none()
    if not routine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routine_not_found")

    routine.name = payload.name.strip()
    routine.description = payload.description.strip() if payload.description else None
    routine.updated_at = datetime.now(UTC)

    # Delete existing exercises and insert new ones
    await db.execute(delete(RoutineExercise).where(RoutineExercise.routine_id == routine.id))
    for ex in payload.exercises:
        re = RoutineExercise(
            routine_id=routine.id,
            exercise_id=ex.exercise_id,
            order_index=ex.order_index,
            target_sets=ex.target_sets,
            rep_min=ex.rep_min,
            rep_max=ex.rep_max,
            rest_seconds=ex.rest_seconds,
        )
        db.add(re)

    await db.commit()
    reloaded = await db.execute(
        select(WorkoutRoutine)
        .options(selectinload(WorkoutRoutine.exercises).selectinload(RoutineExercise.exercise))
        .where(WorkoutRoutine.id == routine.id)
    )
    return _map_routine_to_response(reloaded.scalar_one())


@router.delete("/routines/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routine(
    routine_id: uuid.UUID,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete routine (AC-08 ownership enforced)."""
    routine = await db.execute(
        select(WorkoutRoutine).where(
            WorkoutRoutine.id == routine_id,
            WorkoutRoutine.user_id == current_user.id,
        )
    )
    instance = routine.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routine_not_found")
    await db.delete(instance)
    await db.commit()


@router.post(
    "/routines/{routine_id}/duplicate",
    response_model=RoutineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_routine(
    routine_id: uuid.UUID,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> RoutineResponse:
    """Duplicate routine making an independent copy (AC-35)."""
    stmt = (
        select(WorkoutRoutine)
        .options(selectinload(WorkoutRoutine.exercises))
        .where(
            WorkoutRoutine.id == routine_id,
            WorkoutRoutine.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routine_not_found")

    copy_routine = WorkoutRoutine(
        user_id=current_user.id,
        name=f"{source.name} (Copy)",
        description=source.description,
    )
    db.add(copy_routine)
    await db.flush()

    for se in source.exercises:
        re = RoutineExercise(
            routine_id=copy_routine.id,
            exercise_id=se.exercise_id,
            order_index=se.order_index,
            target_sets=se.target_sets,
            rep_min=se.rep_min,
            rep_max=se.rep_max,
            rest_seconds=se.rest_seconds,
        )
        db.add(re)

    await db.commit()
    reloaded = await db.execute(
        select(WorkoutRoutine)
        .options(selectinload(WorkoutRoutine.exercises).selectinload(RoutineExercise.exercise))
        .where(WorkoutRoutine.id == copy_routine.id)
    )
    return _map_routine_to_response(reloaded.scalar_one())


@router.post("/routines/{routine_id}/start")
async def start_workout_from_routine(
    routine_id: uuid.UUID,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start workout from routine pre-filling exercises with target sets and no sets logged (AC-35)."""
    stmt = (
        select(WorkoutRoutine)
        .options(selectinload(WorkoutRoutine.exercises).selectinload(RoutineExercise.exercise))
        .where(
            WorkoutRoutine.id == routine_id,
            WorkoutRoutine.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    routine = result.scalar_one_or_none()
    if not routine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routine_not_found")

    now = datetime.now(UTC)
    prefilled_exercises = [
        {
            "exercise_id": str(re.exercise_id),
            "exercise_name": re.exercise.name if re.exercise else None,
            "order_index": re.order_index,
            "target_sets": re.target_sets,
            "rep_min": re.rep_min,
            "rep_max": re.rep_max,
            "rest_seconds": re.rest_seconds,
            "sets": [],  # No sets logged yet (AC-35)
        }
        for re in routine.exercises
    ]

    return {
        "routine_id": str(routine.id),
        "routine_name": routine.name,
        "started_at": now.isoformat(),
        "exercises": prefilled_exercises,
    }


# ---------------------------------------------------------------------------
# Workout Logging Endpoints (FR-03, AC-31–38)
# ---------------------------------------------------------------------------


@router.post(
    "/workouts",
    response_model=WorkoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workout(
    payload: WorkoutSessionCreateRequest,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> WorkoutSessionResponse:
    """Atomic workout creation persisting session, exercises, and sets in a single transaction (AC-31, AC-33)."""
    # Verify routine_id belongs to user if provided
    if payload.routine_id:
        rt_chk = await db.execute(
            select(WorkoutRoutine.id).where(
                WorkoutRoutine.id == payload.routine_id,
                WorkoutRoutine.user_id == current_user.id,
            )
        )
        if not rt_chk.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="routine_not_found")

    # Verify exercises exist
    exercise_ids = [ex.exercise_id for ex in payload.exercises]
    if exercise_ids:
        ex_chk = await db.execute(select(Exercise.id).where(Exercise.id.in_(exercise_ids)))
        found_ids = set(ex_chk.scalars().all())
        missing = [eid for eid in exercise_ids if eid not in found_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"exercise_not_found: {missing[0]}",
            )

    session = WorkoutSession(
        user_id=current_user.id,
        routine_id=payload.routine_id,
        started_at=payload.started_at,
        completed_at=payload.completed_at,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(session)
    await db.flush()

    for ex_data in payload.exercises:
        w_ex = WorkoutExercise(
            session_id=session.id,
            exercise_id=ex_data.exercise_id,
            order_index=ex_data.order_index,
            notes=ex_data.notes.strip() if ex_data.notes else None,
        )
        db.add(w_ex)
        await db.flush()

        for s_data in ex_data.sets:
            w_set = WorkoutSet(
                workout_exercise_id=w_ex.id,
                set_number=s_data.set_number,
                reps=s_data.reps,
                load_kg=s_data.load_kg,
                rpe=s_data.rpe,
                is_warmup=s_data.is_warmup,
                completed_at=s_data.completed_at,
            )
            db.add(w_set)

    # Atomic commit
    await db.commit()

    # Reload with full graph in saved order (AC-31)
    reloaded = await db.execute(
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.exercise),
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets),
        )
        .where(WorkoutSession.id == session.id)
    )
    return _map_session_to_response(reloaded.scalar_one())


@router.get("/workouts", response_model=WorkoutHistoryResponse)
async def list_workouts(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, description="Stable keyset cursor (AC-37)"),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> WorkoutHistoryResponse:
    """Paginated workout history using stable keyset cursor without duplicates or gaps (AC-37, AC-38)."""
    stmt = (
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.exercise),
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets),
        )
        .where(WorkoutSession.user_id == current_user.id)
    )

    if cursor:
        try:
            decoded = base64.b64decode(cursor.encode("utf-8")).decode("utf-8")
            cursor_dt_str, cursor_id_str = decoded.split("|")
            cursor_dt = datetime.fromisoformat(cursor_dt_str)
            cursor_id = uuid.UUID(cursor_id_str)
            stmt = stmt.where(
                (WorkoutSession.started_at < cursor_dt)
                | ((WorkoutSession.started_at == cursor_dt) & (WorkoutSession.id < cursor_id))
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_cursor"
            ) from None

    stmt = stmt.order_by(WorkoutSession.started_at.desc(), WorkoutSession.id.desc()).limit(
        limit + 1
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    next_cursor = None
    if len(sessions) > limit:
        last_item = sessions[limit - 1]
        next_raw = f"{last_item.started_at.isoformat()}|{last_item.id}"
        next_cursor = base64.b64encode(next_raw.encode("utf-8")).decode("utf-8")
        items = sessions[:limit]
    else:
        items = sessions

    return WorkoutHistoryResponse(
        items=[_map_session_to_response(s) for s in items],
        next_cursor=next_cursor,
    )


@router.get("/workouts/{session_id}", response_model=WorkoutSessionResponse)
async def get_workout(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> WorkoutSessionResponse:
    """Retrieve full workout session by ID (enforcing ownership, AC-08)."""
    stmt = (
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.exercise),
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets),
        )
        .where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workout_not_found")
    return _map_session_to_response(session)


@router.patch("/workouts/{session_id}", response_model=WorkoutSessionResponse)
async def update_workout(
    session_id: uuid.UUID,
    payload: WorkoutSessionCreateRequest,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> WorkoutSessionResponse:
    """Update workout session, replacing sets and updating analytics (AC-34)."""
    stmt = (
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.exercises))
        .where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workout_not_found")

    session.started_at = payload.started_at
    session.completed_at = payload.completed_at
    session.notes = payload.notes.strip() if payload.notes else None
    session.routine_id = payload.routine_id

    # Delete existing child exercises (cascade removes sets)
    await db.execute(delete(WorkoutExercise).where(WorkoutExercise.session_id == session.id))

    for ex_data in payload.exercises:
        w_ex = WorkoutExercise(
            session_id=session.id,
            exercise_id=ex_data.exercise_id,
            order_index=ex_data.order_index,
            notes=ex_data.notes.strip() if ex_data.notes else None,
        )
        db.add(w_ex)
        await db.flush()

        for s_data in ex_data.sets:
            w_set = WorkoutSet(
                workout_exercise_id=w_ex.id,
                set_number=s_data.set_number,
                reps=s_data.reps,
                load_kg=s_data.load_kg,
                rpe=s_data.rpe,
                is_warmup=s_data.is_warmup,
                completed_at=s_data.completed_at,
            )
            db.add(w_set)

    await db.commit()

    reloaded = await db.execute(
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.exercise),
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets),
        )
        .where(WorkoutSession.id == session_id)
        .execution_options(populate_existing=True)
    )
    return _map_session_to_response(reloaded.scalar_one())


@router.delete("/workouts/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user_required),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete workout and all child sets, affecting no other user's data (AC-34)."""
    stmt = select(WorkoutSession).where(
        WorkoutSession.id == session_id,
        WorkoutSession.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workout_not_found")

    await db.delete(session)
    await db.commit()
