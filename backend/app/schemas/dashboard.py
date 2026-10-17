"""Dashboard and insights schemas (spec §7, §5.9, FR-13, AC-85–87)."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.nutrition_log import PlannedVsLoggedDayResponse


class DashboardSummaryResponse(BaseModel):
    """Combined dashboard overview response (FR-13, AC-85)."""

    weekly_sessions: int
    weekly_volume_kg: Decimal
    pr_count: int
    active_goal_calories: int | None = None
    active_goal_protein: int | None = None
    active_plan_id: UUID | None = None
    planned_vs_logged: list[PlannedVsLoggedDayResponse]
    disclaimer: str


class InsightItemResponse(BaseModel):
    """Descriptive, non-causal insight with mandatory metadata (AC-86, AC-87)."""

    id: str
    title: str
    window: str
    n: int
    statement: str
    limitations: str
    evidence: dict[str, Any]


class InsightsResponse(BaseModel):
    """Collection of insights or explanation when minimum threshold is unmet (AC-86)."""

    has_enough_data: bool
    message: str | None = None
    insights: list[InsightItemResponse]
    disclaimer: str
