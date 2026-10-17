"""Combined dashboard and non-causal insights router (spec §7, §5.9, FR-13, AC-85–87)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_required, get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse, InsightsResponse
from app.services.dashboard import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get(
    "/api/dashboard",
    response_model=DashboardSummaryResponse,
)
async def get_dashboard(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    """Fetch combined workout consistency, volume, PRs, and planned vs logged summary (AC-85)."""
    service = DashboardService(db)
    return await service.get_dashboard(current_user.id)


@router.get(
    "/api/insights",
    response_model=InsightsResponse,
)
async def get_insights(
    exercise_id: UUID | None = None,
    window: str = Query("last_4_weeks", pattern="^(last_4_weeks|last_12_weeks)$"),
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> InsightsResponse:
    """Fetch descriptive non-causal strength insights with min 3 sessions threshold (AC-86, AC-87)."""
    service = DashboardService(db)
    return await service.get_insights(current_user.id, exercise_id, window)
