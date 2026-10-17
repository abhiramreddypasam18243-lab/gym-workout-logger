"""Analytics API endpoints for strength trends, PRs, and consistency (spec §5.2, §7, AC-39–44)."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_session
from app.database import get_db
from app.models.user import Session, User
from app.services.strength import StrengthAnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/strength")
async def get_strength_analytics(
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    exercise_id: uuid.UUID = Query(..., description="ID of exercise to analyse"),
    days: int | None = Query(None, ge=1, le=730, description="Window in days"),
    start_date: date | None = Query(None, description="Start date filter"),
    end_date: date | None = Query(None, description="End date filter"),
) -> list[dict]:
    """Return best e1RM per session date in user timezone (spec §5.2, FR-05, AC-42).

    Converts units for lb users, labels estimates, and returns empty list with 200 when no data.
    """
    user, _session = auth
    tz_str = user.profile.timezone if user.profile else "UTC"
    units_str = user.profile.units if user.profile else "kg"

    service = StrengthAnalyticsService(db)
    return await service.get_exercise_e1rm_trends(
        user_id=user.id,
        exercise_id=exercise_id,
        user_timezone=tz_str,
        units=units_str,
        days=days,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/consistency")
async def get_weekly_consistency(
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    weeks: int = Query(12, ge=1, le=52, description="Number of weeks to evaluate"),
) -> dict:
    """Return workout sessions per week in user timezone (spec §5.2, AC-44).

    Rules:
    - Monday, Wednesday, Saturday give 3 for that week.
    - Weeks with none give 0.
    - Sessions with only warm-up sets are not counted.
    """
    user, _session = auth
    tz_str = user.profile.timezone if user.profile else "UTC"
    target = user.profile.weekly_session_target if user.profile else 3

    service = StrengthAnalyticsService(db)
    weekly_data = await service.get_weekly_consistency(
        user_id=user.id,
        user_timezone=tz_str,
        weeks=weeks,
    )

    return {
        "weekly_target": target,
        "weeks": weekly_data,
    }


@router.get("/prs/{exercise_id}")
async def get_exercise_prs(
    exercise_id: uuid.UUID,
    auth: Annotated[tuple[User, Session], Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    """Return chronological PR milestones for an exercise (spec §5.2, AC-41)."""
    user, _session = auth
    units_str = user.profile.units if user.profile else "kg"

    service = StrengthAnalyticsService(db)
    return await service.get_exercise_prs(
        user_id=user.id,
        exercise_id=exercise_id,
        units=units_str,
    )
