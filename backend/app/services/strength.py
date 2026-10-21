"""Strength analytics service: trends, consistency, PRs, and volume (spec §5.2, AC-39–44)."""

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.strength import (
    StrengthSetInput,
    calculate_epley_e1rm,
    detect_personal_records,
)
from app.domain.units import kg_to_lb
from app.models.workout import WorkoutExercise, WorkoutSession


class StrengthAnalyticsService:
    """Service implementing strength metrics and trend analytics (spec §5.2, FR-05, AC-39–44)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_exercise_e1rm_trends(
        self,
        user_id: uuid.UUID,
        exercise_id: uuid.UUID,
        user_timezone: str = "UTC",
        units: str = "kg",
        days: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Return best e1RM per session date in user timezone within the window (AC-42).

        Converts units for lb users (to 1 decimal place), labels estimates as estimated (AC-39),
        and returns an empty list if there is no data (AC-42).
        """
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        # Query all workout sessions for user containing this exercise
        stmt = (
            select(WorkoutSession)
            .join(WorkoutExercise, WorkoutExercise.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutExercise.exercise_id == exercise_id,
            )
            .options(
                selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
            )
            .order_by(WorkoutSession.started_at.asc())
        )

        result = await self.db.execute(stmt)
        sessions = result.scalars().unique().all()

        if not sessions:
            return []

        # Determine cutoff if window is specified
        now_local = datetime.now(tz)
        cutoff_date = None
        if days is not None:
            cutoff_date = (now_local - timedelta(days=days)).date()

        # Group working sets by local session date
        daily_best: dict[date, dict[str, Any]] = {}

        for sess in sessions:
            # Convert started_at to user's timezone
            sess_time = sess.started_at
            if sess_time.tzinfo is None:
                sess_time = sess_time.replace(tzinfo=UTC)
            local_dt = sess_time.astimezone(tz)
            sess_date = local_dt.date()

            if cutoff_date and sess_date < cutoff_date:
                continue
            if start_date and sess_date < start_date:
                continue
            if end_date and sess_date > end_date:
                continue

            # Evaluate sets for the requested exercise in this session
            for we in sess.exercises:
                if we.exercise_id != exercise_id:
                    continue

                for s in we.sets:
                    if s.is_warmup:
                        continue  # Exclude warmups (AC-39)

                    e1rm_res = calculate_epley_e1rm(
                        load_kg=Decimal(str(s.load_kg)),
                        reps=s.reps,
                        is_warmup=s.is_warmup,
                    )
                    if e1rm_res.e1rm is None:
                        continue

                    current_best = daily_best.get(sess_date)
                    if current_best is None or e1rm_res.e1rm > current_best["e1rm_kg"]:
                        daily_best[sess_date] = {
                            "session_id": str(sess.id),
                            "date": sess_date.isoformat(),
                            "e1rm_kg": e1rm_res.e1rm,
                            "load_kg": Decimal(str(s.load_kg)),
                            "reps": s.reps,
                            "set_number": s.set_number,
                        }

        # Format output items, converting units if user prefers lb (AC-42, AC-96)
        formatted_trends: list[dict[str, Any]] = []
        is_lb = units.lower() == "lb"

        for s_date in sorted(daily_best.keys()):
            item = daily_best[s_date]
            e1rm_val = item["e1rm_kg"]
            load_val = item["load_kg"]

            if is_lb:
                # Convert exact decimals for lb display (AC-16, AC-42, AC-96)
                e1rm_disp_dec = kg_to_lb(e1rm_val)
                load_disp_dec = kg_to_lb(load_val)
                display_e1rm = f"{e1rm_disp_dec:.1f}"
                display_load = f"{load_disp_dec:.1f}"
            else:
                display_e1rm = f"{e1rm_val:.1f}"
                display_load = f"{load_val:.1f}"

            formatted_trends.append({
                "session_id": item["session_id"],
                "date": item["date"],
                "e1rm": display_e1rm,
                "e1rm_exact": str(e1rm_val.normalize()),
                "load": display_load,
                "reps": item["reps"],
                "unit": "lb" if is_lb else "kg",
                "is_estimated": True,  # Always labelled estimated (AC-39, AC-42)
            })

        return formatted_trends

    async def get_weekly_consistency(
        self,
        user_id: uuid.UUID,
        user_timezone: str = "UTC",
        weeks: int = 12,
    ) -> list[dict[str, Any]]:
        """Return workout sessions per week in user timezone (spec §5.2, AC-44).

        Rules:
        - Only counts sessions with at least one working set (warm-up only sessions not counted).
        - A week with no valid sessions gives 0.
        - Sessions on Monday, Wednesday, Saturday give 3 for that week.
        """
        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        # Fetch all user sessions with their exercises and sets
        stmt = (
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id)
            .options(
                selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
            )
            .order_by(WorkoutSession.started_at.asc())
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().unique().all()

        now_local = datetime.now(tz)
        today_local = now_local.date()

        # Start of current week (Monday)
        current_week_monday = today_local - timedelta(days=today_local.weekday())
        earliest_monday = current_week_monday - timedelta(weeks=weeks - 1)

        # Count valid sessions per Monday-based week
        week_counts: dict[date, int] = defaultdict(int)

        for sess in sessions:
            # Check if session has at least one working set (AC-44)
            has_working_set = False
            for we in sess.exercises:
                for s in we.sets:
                    if not s.is_warmup:
                        has_working_set = True
                        break
                if has_working_set:
                    break

            if not has_working_set:
                # Sessions with only warm-up sets are not counted (AC-44)
                continue

            sess_time = sess.started_at
            if sess_time.tzinfo is None:
                sess_time = sess_time.replace(tzinfo=UTC)
            local_dt = sess_time.astimezone(tz)
            sess_date = local_dt.date()

            # Week start (Monday)
            week_monday = sess_date - timedelta(days=sess_date.weekday())
            if week_monday >= earliest_monday:
                week_counts[week_monday] += 1

        # Build complete chronological weekly list (including 0s, AC-44)
        output: list[dict[str, Any]] = []
        for i in range(weeks):
            week_mon = earliest_monday + timedelta(weeks=i)
            week_sun = week_mon + timedelta(days=6)
            output.append({
                "week_start": week_mon.isoformat(),
                "week_end": week_sun.isoformat(),
                "session_count": week_counts[week_mon],
            })

        return output

    async def get_exercise_prs(
        self,
        user_id: uuid.UUID,
        exercise_id: uuid.UUID,
        units: str = "kg",
    ) -> list[dict[str, Any]]:
        """Detect personal records for an exercise chronologically (spec §5.2, AC-41).

        First working set is baseline, strictly greater e1RM is PR, equal is not.
        Deleting a set recomputes PRs automatically.
        """
        stmt = (
            select(WorkoutSession)
            .join(WorkoutExercise, WorkoutExercise.session_id == WorkoutSession.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutExercise.exercise_id == exercise_id,
            )
            .options(
                selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
            )
            .order_by(WorkoutSession.started_at.asc())
        )
        result = await self.db.execute(stmt)
        sessions = result.scalars().unique().all()

        # Collect all working sets
        domain_sets: list[StrengthSetInput] = []
        set_meta_map: dict[tuple[Any, ...], dict[str, Any]] = {}

        for sess in sessions:
            for we in sess.exercises:
                if we.exercise_id != exercise_id:
                    continue
                for s in we.sets:
                    if s.is_warmup:
                        continue
                    set_input = StrengthSetInput(
                        load_kg=Decimal(str(s.load_kg)),
                        reps=s.reps,
                        is_warmup=s.is_warmup,
                        set_number=s.set_number,
                        completed_at=s.completed_at or sess.started_at,
                    )
                    domain_sets.append(set_input)
                    set_meta_map[(set_input.completed_at, set_input.set_number)] = {
                        "set_id": str(s.id),
                        "session_id": str(sess.id),
                        "completed_at": (s.completed_at or sess.started_at).isoformat(),
                    }

        # Detect PRs using domain logic
        pr_results = detect_personal_records(domain_sets)

        is_lb = units.lower() == "lb"
        output: list[dict[str, Any]] = []

        for pr in pr_results:
            key = (pr.set_input.completed_at, pr.set_input.set_number)
            meta = set_meta_map.get(key, {})
            load_val = pr.set_input.load_kg
            e1rm_val = pr.e1rm

            if is_lb:
                load_disp = f"{kg_to_lb(load_val):.1f}"
                e1rm_disp = f"{kg_to_lb(e1rm_val):.1f}" if e1rm_val is not None else None
            else:
                load_disp = f"{load_val:.1f}"
                e1rm_disp = f"{e1rm_val:.1f}" if e1rm_val is not None else None

            output.append({
                "set_id": meta.get("set_id"),
                "session_id": meta.get("session_id"),
                "completed_at": meta.get("completed_at"),
                "set_number": pr.set_input.set_number,
                "reps": pr.set_input.reps,
                "load": load_disp,
                "e1rm": e1rm_disp,
                "e1rm_exact": str(e1rm_val.normalize()) if e1rm_val is not None else None,
                "unit": "lb" if is_lb else "kg",
                "is_baseline": pr.is_baseline,
                "is_pr": pr.is_pr,
                "is_estimated": True,
            })

        return output
