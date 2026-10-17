"""Combined dashboard and non-causal insights service (spec §6, §5.9, FR-13, AC-85–87)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.insights import (
    generate_strength_trend_insight,
)
from app.domain.strength import calculate_epley_e1rm
from app.models.nutrition import MealPlan, NutritionGoal
from app.models.user import UserProfile
from app.models.workout import Exercise, WorkoutExercise, WorkoutSession
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    InsightItemResponse,
    InsightsResponse,
)
from app.services.nutrition_logs import NutritionLogService
from app.services.planner import DISCLAIMER_TEXT


class DashboardService:
    """Computes combined workout and nutrition metrics, and generates descriptive insights."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.log_service = NutritionLogService(db)

    async def get_user_timezone(self, user_id: UUID) -> ZoneInfo:
        """Fetch user timezone or fallback to UTC."""
        stmt = select(UserProfile.timezone).where(UserProfile.user_id == user_id)
        tz_str = (await self.db.execute(stmt)).scalar_one_or_none()
        if tz_str:
            try:
                return ZoneInfo(tz_str)
            except Exception:
                pass
        return ZoneInfo("UTC")

    async def get_dashboard(self, user_id: UUID) -> DashboardSummaryResponse:
        """Fetch combined dashboard summary with empty states for new users (AC-85)."""
        tz = await self.get_user_timezone(user_id)
        now_local = datetime.now(UTC).astimezone(tz)
        today = now_local.date()

        # Current week window: Monday to Sunday
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # 1. Weekly workout sessions count (AC-85)
        w_stmt = select(WorkoutSession).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.started_at >= datetime.combine(start_of_week, datetime.min.time(), tzinfo=tz),
            WorkoutSession.started_at <= datetime.combine(end_of_week, datetime.max.time(), tzinfo=tz),
        ).options(
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
        )
        week_workouts = (await self.db.execute(w_stmt)).scalars().all()
        weekly_sessions = len(week_workouts)

        # 2. Weekly volume lifted (kg)
        weekly_volume = Decimal("0")
        for w in week_workouts:
            for ex in w.exercises:
                for s in ex.sets:
                    if not s.is_warmup and s.load_kg and s.reps:
                        weekly_volume += s.load_kg * Decimal(str(s.reps))

        # 3. All-time PR count
        # In this context, count exercises with recorded workout history
        pr_stmt = (
            select(func.count(func.distinct(WorkoutExercise.exercise_id)))
            .join(WorkoutSession, WorkoutExercise.session_id == WorkoutSession.id)
            .where(WorkoutSession.user_id == user_id)
        )
        pr_count = (await self.db.execute(pr_stmt)).scalar() or 0

        # 4. Active meal plan and nutrition goal
        p_stmt = (
            select(MealPlan)
            .where(MealPlan.user_id == user_id)
            .order_by(MealPlan.created_at.desc())
        )
        active_plan = (await self.db.execute(p_stmt)).scalars().first()

        g_stmt = (
            select(NutritionGoal)
            .where(NutritionGoal.user_id == user_id, NutritionGoal.effective_from <= today)
            .order_by(NutritionGoal.effective_from.desc())
        )
        active_goal = (await self.db.execute(g_stmt)).scalars().first()

        # 5. Planned vs Logged analytics for current week
        analytics = await self.log_service.get_planned_vs_logged_analytics(
            user_id=user_id,
            start_date=start_of_week,
            end_date=end_of_week,
        )

        return DashboardSummaryResponse(
            weekly_sessions=weekly_sessions,
            weekly_volume_kg=weekly_volume,
            pr_count=pr_count,
            active_goal_calories=active_goal.calorie_target_kcal if active_goal else None,
            active_goal_protein=active_goal.protein_target_g if active_goal else None,
            active_plan_id=active_plan.id if active_plan else None,
            planned_vs_logged=analytics.days,
            disclaimer=DISCLAIMER_TEXT,
        )

    async def get_insights(
        self,
        user_id: UUID,
        exercise_id: UUID | None = None,
        window: str = "last_4_weeks",
    ) -> InsightsResponse:
        """Generate non-causal descriptive insights with min 3 sessions requirement (AC-86, AC-87)."""
        tz = await self.get_user_timezone(user_id)
        now_local = datetime.now(UTC).astimezone(tz)
        today = now_local.date()

        # Determine window days
        window_days = 28 if window == "last_4_weeks" else 84
        start_date = today - timedelta(days=window_days)
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tz)

        # If exercise_id is provided, check session count for that exercise
        if exercise_id:
            e_stmt = select(Exercise).where(Exercise.id == exercise_id)
            target_ex = (await self.db.execute(e_stmt)).scalars().first()
            if not target_ex:
                return InsightsResponse(
                    has_enough_data=False,
                    message="Exercise not found",
                    insights=[],
                    disclaimer=DISCLAIMER_TEXT,
                )

            # Query workouts containing this exercise in window
            we_stmt = (
                select(WorkoutExercise)
                .join(WorkoutSession, WorkoutExercise.session_id == WorkoutSession.id)
                .where(
                    WorkoutSession.user_id == user_id,
                    WorkoutExercise.exercise_id == exercise_id,
                    WorkoutSession.started_at >= start_dt,
                )
                .options(
                    selectinload(WorkoutExercise.sets),
                    selectinload(WorkoutExercise.session),
                )
                .order_by(WorkoutSession.started_at.asc())
            )
            ex_sessions = (await self.db.execute(we_stmt)).scalars().all()

            # AC-86: With fewer than 3 sessions of an exercise in the window,
            # no trend insight is produced and the response says there is not enough data.
            if len(ex_sessions) < 3:
                return InsightsResponse(
                    has_enough_data=False,
                    message="Not enough data for this exercise in the selected window (minimum 3 sessions required).",
                    insights=[],
                    disclaimer=DISCLAIMER_TEXT,
                )

            # Calculate best e1RM per session
            e1rm_list: list[Decimal] = []
            dates_list: list[str] = []
            for ws in ex_sessions:
                best_e1rm = Decimal("0")
                for s in ws.sets:
                    if not s.is_warmup and s.load_kg and s.reps:
                        res = calculate_epley_e1rm(s.load_kg, s.reps, is_warmup=s.is_warmup)
                        if res.e1rm and res.e1rm > best_e1rm:
                            best_e1rm = res.e1rm
                if best_e1rm > Decimal("0"):
                    e1rm_list.append(best_e1rm)
                    dates_list.append(ws.session.started_at.astimezone(tz).date().isoformat())

            if len(e1rm_list) < 3:
                return InsightsResponse(
                    has_enough_data=False,
                    message="Not enough data for this exercise in the selected window (minimum 3 sessions required).",
                    insights=[],
                    disclaimer=DISCLAIMER_TEXT,
                )

            gen = generate_strength_trend_insight(target_ex.name, window, e1rm_list, dates_list)
            if not gen:
                return InsightsResponse(
                    has_enough_data=False,
                    message="Not enough data for this exercise in the selected window (minimum 3 sessions required).",
                    insights=[],
                    disclaimer=DISCLAIMER_TEXT,
                )

            return InsightsResponse(
                has_enough_data=True,
                message=None,
                insights=[
                    InsightItemResponse(
                        id=gen.id,
                        title=gen.title,
                        window=gen.window,
                        n=gen.n,
                        statement=gen.statement,
                        limitations=gen.limitations,
                        evidence=gen.evidence,
                    )
                ],
                disclaimer=DISCLAIMER_TEXT,
            )

        # General insights if no exercise specified
        # Check overall workout sessions in window
        w_stmt = (
            select(WorkoutSession)
            .where(WorkoutSession.user_id == user_id, WorkoutSession.started_at >= start_dt)
            .options(
                selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets),
                selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.exercise),
            )
            .order_by(WorkoutSession.started_at.asc())
        )
        workouts = (await self.db.execute(w_stmt)).scalars().all()

        if len(workouts) < 3:
            return InsightsResponse(
                has_enough_data=False,
                message="Not enough data in the selected window (minimum 3 sessions required).",
                insights=[],
                disclaimer=DISCLAIMER_TEXT,
            )

        # Group exercises and generate insight for the most frequent exercise with >= 3 sessions
        ex_counts: dict[str, list[tuple[Decimal, str]]] = {}
        for w in workouts:
            w_date = w.started_at.astimezone(tz).date().isoformat()
            for we in w.exercises:
                best_e = Decimal("0")
                for s in we.sets:
                    if not s.is_warmup and s.load_kg and s.reps:
                        calc = calculate_epley_e1rm(s.load_kg, s.reps, is_warmup=s.is_warmup)
                        if calc.e1rm and calc.e1rm > best_e:
                            best_e = calc.e1rm
                if best_e > Decimal("0") and we.exercise:
                    ex_name = we.exercise.name
                    if ex_name not in ex_counts:
                        ex_counts[ex_name] = []
                    ex_counts[ex_name].append((best_e, w_date))

        generated_list: list[InsightItemResponse] = []
        for name, data in ex_counts.items():
            if len(data) >= 3:
                e_vals = [d[0] for d in data]
                d_strs = [d[1] for d in data]
                insight = generate_strength_trend_insight(name, window, e_vals, d_strs)
                if insight:
                    generated_list.append(
                        InsightItemResponse(
                            id=insight.id,
                            title=insight.title,
                            window=insight.window,
                            n=insight.n,
                            statement=insight.statement,
                            limitations=insight.limitations,
                            evidence=insight.evidence,
                        )
                    )

        if not generated_list:
            return InsightsResponse(
                has_enough_data=False,
                message="No single exercise had at least 3 sessions in the selected window.",
                insights=[],
                disclaimer=DISCLAIMER_TEXT,
            )

        return InsightsResponse(
            has_enough_data=True,
            message=None,
            insights=generated_list[:3],  # Return up to 3 top insights
            disclaimer=DISCLAIMER_TEXT,
        )
