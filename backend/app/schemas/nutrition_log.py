"""Nutrition logging and planned vs logged comparison schemas (spec §7, §5.8, FR-12, AC-82–84)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NutritionLogItemCreate(BaseModel):
    """Payload to log a food or recipe intake item (AC-82)."""

    model_config = ConfigDict(extra="forbid")

    food_id: UUID | None = None
    recipe_id: UUID | None = None
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit: str = Field(default="g", min_length=1, max_length=30)

    @model_validator(mode="after")
    def validate_food_or_recipe(self) -> "NutritionLogItemCreate":
        if self.food_id is None and self.recipe_id is None:
            raise ValueError("Either food_id or recipe_id must be provided")
        if self.food_id is not None and self.recipe_id is not None:
            raise ValueError("Cannot specify both food_id and recipe_id on the same item")
        return self


class NutritionLogCreate(BaseModel):
    """Payload to log an intake session (AC-82)."""

    model_config = ConfigDict(extra="forbid")

    consumed_at: datetime
    meal_type: str = Field(..., min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=1000)
    items: list[NutritionLogItemCreate] = Field(..., min_length=1)


class NutritionLogUpdate(BaseModel):
    """Payload to update an existing intake log (AC-82)."""

    model_config = ConfigDict(extra="forbid")

    consumed_at: datetime | None = None
    meal_type: str | None = None
    notes: str | None = None
    items: list[NutritionLogItemCreate] | None = None


class NutritionLogItemResponse(BaseModel):
    """Serialized logged intake item with historical snapshot (AC-54, AC-82)."""

    id: UUID
    food_id: UUID | None
    food_name: str | None = None
    recipe_id: UUID | None
    recipe_title: str | None = None
    quantity: Decimal
    unit: str
    nutrient_snapshot: dict[str, Any] | None
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal


class NutritionLogResponse(BaseModel):
    """Serialized intake log session with aggregated totals (AC-82)."""

    id: UUID
    consumed_at: datetime
    meal_type: str
    source_type: str
    notes: str | None
    items: list[NutritionLogItemResponse]
    total_calories: Decimal
    total_protein_g: Decimal
    total_carbs_g: Decimal
    total_fat_g: Decimal


class PlannedVsLoggedDayResponse(BaseModel):
    """Daily planned vs logged comparison report (spec §5.8, AC-83, AC-84)."""

    date: date
    is_logged: bool
    planned_calories: Decimal | None = None
    logged_calories: Decimal | None = None
    calories_difference: Decimal | None = None
    calories_difference_pct: Decimal | None = None
    planned_protein_g: Decimal | None = None
    logged_protein_g: Decimal | None = None
    protein_difference_g: Decimal | None = None
    protein_difference_pct: Decimal | None = None
    is_within_range: bool | None = None
    status_label: str


class NutritionAnalyticsResponse(BaseModel):
    """Planned versus logged analytics summary for a requested date range (AC-83, AC-84)."""

    start_date: date
    end_date: date
    days_logged_count: int
    average_logged_calories: Decimal | None = None
    average_logged_protein_g: Decimal | None = None
    days: list[PlannedVsLoggedDayResponse]
    disclaimer: str
