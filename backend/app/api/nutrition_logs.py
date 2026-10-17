"""Nutrition intake logging and planned vs logged analytics router (spec §7, §5.8, FR-12, AC-82–84)."""

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_nutrition_access, get_db, verify_csrf
from app.models.user import User
from app.schemas.nutrition_log import (
    NutritionAnalyticsResponse,
    NutritionLogCreate,
    NutritionLogResponse,
    NutritionLogUpdate,
)
from app.services.nutrition_logs import NutritionLogService

router = APIRouter(tags=["nutrition-logs"])


@router.post(
    "/api/nutrition/logs",
    response_model=NutritionLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_nutrition_log(
    payload: NutritionLogCreate,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> NutritionLogResponse:
    """Log food or recipe intake with historical nutrient snapshots (AC-82)."""
    current_user, _ = auth
    service = NutritionLogService(db)
    return await service.create_log(current_user.id, payload)


@router.get(
    "/api/nutrition/logs",
    response_model=list[NutritionLogResponse],
)
async def list_nutrition_logs(
    from_date: date | None = None,
    to_date: date | None = None,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    db: AsyncSession = Depends(get_db),
) -> list[NutritionLogResponse]:
    """List logged meals filtered by date range in the user's timezone (AC-84)."""
    current_user, _ = auth
    service = NutritionLogService(db)
    return await service.list_logs(current_user.id, from_date, to_date)


@router.get(
    "/api/nutrition/logs/{log_id}",
    response_model=NutritionLogResponse,
)
async def get_nutrition_log(
    log_id: UUID,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    db: AsyncSession = Depends(get_db),
) -> NutritionLogResponse:
    """Fetch details of a specific intake log (SEC4)."""
    current_user, _ = auth
    service = NutritionLogService(db)
    return await service.get_log_or_404(log_id, current_user.id)


@router.patch(
    "/api/nutrition/logs/{log_id}",
    response_model=NutritionLogResponse,
)
async def update_nutrition_log(
    log_id: UUID,
    payload: NutritionLogUpdate,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> NutritionLogResponse:
    """Update intake log quantity or items with snapshot recomputation (AC-82)."""
    current_user, _ = auth
    service = NutritionLogService(db)
    return await service.update_log(current_user.id, log_id, payload)


@router.delete(
    "/api/nutrition/logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_nutrition_log(
    log_id: UUID,
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    _: None = Depends(verify_csrf),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an intake log and update day totals (AC-82)."""
    current_user, _ = auth
    service = NutritionLogService(db)
    await service.delete_log(current_user.id, log_id)


@router.get(
    "/api/analytics/nutrition",
    response_model=NutritionAnalyticsResponse,
)
async def get_nutrition_analytics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    auth: tuple[User, Any] = Depends(check_nutrition_access),
    db: AsyncSession = Depends(get_db),
) -> NutritionAnalyticsResponse:
    """Planned versus logged comparison report (spec §5.8, AC-83, AC-84)."""
    current_user, _ = auth
    service = NutritionLogService(db)
    return await service.get_planned_vs_logged_analytics(current_user.id, start_date, end_date)
