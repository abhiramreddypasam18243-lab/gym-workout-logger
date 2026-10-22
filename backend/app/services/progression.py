"""Progressive overload hints and weekly set volume per muscle (D-33, D-34, AC-123–125)."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.domain.progression import count_working_sets_by_muscle, suggest_next_load
from app.domain.strength import StrengthSetInput
from app.domain.units import kg_to_lb, lb_to_kg
from app.models.workout import (
    Exercise,
    MuscleSetTarget,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)

HINT_NOTE = "A rule-based suggestion from your last session, not coaching advice. Only add load with good form."


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def _local_date(moment: datetime, tz: ZoneInfo) -> date:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(tz).date()


class ProgressionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _visible_exercise(self, user_id: uuid.UUID, exercise_id: uuid.UUID) -> Exercise:
        stmt = select(Exercise).where(
            Exercise.id == exercise_id,
            or_(Exercise.owner_user_id.is_(None), Exercise.owner_user_id == user_id),
        )
        exercise = (await self.db.execute(stmt)).scalar_one_or_none()
        if exercise is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="exercise_not_found")
        return exercise

    async def next_load_hint(
        self,
        user_id: uuid.UUID,
        exercise_id: uuid.UUID,
        rep_min: int | None,
        rep_max: int | None,
        units: str = "kg",
        user_timezone: str = "UTC",
    ) -> dict[str, Any]:
        """Hint from the most recent session with working sets of this exercise (AC-123)."""
        exercise = await self._visible_exercise(user_id, exercise_id)
        low = rep_min if rep_min is not None else settings.DEFAULT_REP_MIN
        high = rep_max if rep_max is not None else settings.DEFAULT_REP_MAX
        if high < low:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="rep_max_below_rep_min")

        is_lb = units.lower() == "lb"
        lower_body = exercise.primary_muscle.strip().lower() in settings.LOWER_BODY_MUSCLES
        if is_lb:
            step_lb = settings.OVERLOAD_STEP_LOWER_LB if lower_body else settings.OVERLOAD_STEP_UPPER_LB
            step_kg = lb_to_kg(step_lb)
        else:
            step_kg = settings.OVERLOAD_STEP_LOWER_KG if lower_body else settings.OVERLOAD_STEP_UPPER_KG

        stmt = (
            select(WorkoutSession)
            .join(WorkoutExercise, WorkoutExercise.session_id == WorkoutSession.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutExercise.exercise_id == exercise_id,
                WorkoutSet.is_warmup.is_(False),
            )
            .options(selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets))
            .order_by(WorkoutSession.started_at.desc(), WorkoutSession.id.desc())
            .limit(1)
        )
        last = (await self.db.execute(stmt)).scalars().first()
        base: dict[str, Any] = {
            "exercise_id": str(exercise_id),
            "unit": "lb" if is_lb else "kg",
            "rep_min": low,
            "rep_max": high,
            "note": HINT_NOTE,
        }
        if last is None:
            return {**base, "action": "no_history"}

        sets = [
            StrengthSetInput(
                load_kg=Decimal(str(s.load_kg)), reps=s.reps, is_warmup=s.is_warmup, set_number=s.set_number
            )
            for we in last.exercises
            if we.exercise_id == exercise_id
            for s in we.sets
        ]
        hint = suggest_next_load(sets, low, high, step_kg)
        if hint is None:
            return {**base, "action": "no_history"}

        def show(kg: Decimal) -> str:
            # lb users see their own numbers: the step is whole pounds, so round-trip exactly
            return f"{kg_to_lb(kg):.1f}" if is_lb else f"{kg:.1f}"

        return {
            **base,
            "action": hint.action,
            "last_session_date": _local_date(last.started_at, _zone(user_timezone)).isoformat(),
            "top_load": show(hint.top_load_kg),
            "suggested_load": show(hint.suggested_load_kg),
            "reps_at_top_load": list(hint.reps_at_top_load),
            "reason": hint.reason,
        }

    async def weekly_volume(self, user_id: uuid.UUID, user_timezone: str = "UTC") -> dict[str, Any]:
        """Working sets per primary muscle this week (Monday start, user timezone) and targets (AC-125)."""
        tz = _zone(user_timezone)
        today = datetime.now(tz).date()
        monday = today - timedelta(days=today.weekday())
        # Sessions starting within a day either side cover any timezone; filter by local date below
        window_start = datetime.combine(monday - timedelta(days=1), datetime.min.time(), tzinfo=UTC)

        stmt = (
            select(WorkoutSession.started_at, Exercise.primary_muscle, WorkoutSet.is_warmup)
            .join(WorkoutExercise, WorkoutExercise.session_id == WorkoutSession.id)
            .join(Exercise, Exercise.id == WorkoutExercise.exercise_id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(WorkoutSession.user_id == user_id, WorkoutSession.started_at >= window_start)
        )
        rows = (await self.db.execute(stmt)).all()
        counts = count_working_sets_by_muscle(
            (muscle, is_warmup)
            for started_at, muscle, is_warmup in rows
            if monday <= _local_date(started_at, tz) <= monday + timedelta(days=6)
        )
        targets = await self._targets(user_id)

        muscles = sorted(set(counts) | set(targets))
        return {
            "week_start": monday.isoformat(),
            "week_end": (monday + timedelta(days=6)).isoformat(),
            "muscles": [
                {
                    "muscle": m,
                    "sets": counts.get(m, 0),
                    "target": targets.get(m),
                    "met": m in targets and counts.get(m, 0) >= targets[m],
                }
                for m in muscles
            ],
        }

    async def _targets(self, user_id: uuid.UUID) -> dict[str, int]:
        rows = (await self.db.execute(select(MuscleSetTarget).where(MuscleSetTarget.user_id == user_id))).scalars()
        return {t.muscle: t.weekly_sets for t in rows}

    async def replace_targets(self, user_id: uuid.UUID, targets: dict[str, int]) -> dict[str, int]:
        """Replace all of the user's weekly set targets (AC-125)."""
        clean: dict[str, int] = {}
        for muscle, sets in targets.items():
            name = muscle.strip().lower()
            if not name or len(name) > 50:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid_muscle")
            clean[name] = sets
        await self.db.execute(delete(MuscleSetTarget).where(MuscleSetTarget.user_id == user_id))
        self.db.add_all(MuscleSetTarget(user_id=user_id, muscle=m, weekly_sets=n) for m, n in clean.items())
        await self.db.commit()
        return await self._targets(user_id)
