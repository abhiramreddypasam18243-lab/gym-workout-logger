"""Pydantic schemas for meal plan generation, inspection, and infeasibility explanations (spec §7, FR-08, AC-56–72)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MealPlanGenerateRequest(BaseModel):
    """Payload for POST /api/meal-plans/generate (spec §7, AC-56–72)."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    days: int = Field(default=7, ge=1, le=14)
    meal_slots: list[str] = Field(
        default=["breakfast", "lunch", "dinner", "snack"], min_length=1, max_length=6
    )
    max_minutes: int | None = Field(default=None, ge=5, le=300)
    daily_budget_minor: int | None = Field(default=None, ge=0)


class FilterRemovedCount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filter: str
    removed: int


class InfeasibleExplanationResponse(BaseModel):
    """Returned with HTTP 200 when hard filters leave a slot with no candidates (AC-62, AC-72)."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["infeasible"] = "infeasible"
    slot: str
    day: str
    filters: list[FilterRemovedCount]
    relaxable: list[str]
    message: str


class MealNutrientSummary(BaseModel):
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal = Decimal("0")


class PlannedMealItemResponse(BaseModel):
    id: UUID
    food_id: UUID | None
    ingredient_name: str
    quantity: Decimal
    unit: str
    nutrient_snapshot: dict[str, Any] | None


class PlannedMealResponse(BaseModel):
    id: UUID
    plan_date: date
    meal_type: str
    recipe_id: UUID | None
    title: str
    servings: Decimal
    sort_order: int
    cuisine_code: str | None = None
    total_minutes: int = 0
    cost_minor: int | None = None
    nutrients: MealNutrientSummary
    items: list[PlannedMealItemResponse] = []


class DayNutrientTotal(BaseModel):
    plan_date: date
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal = Decimal("0")
    calorie_target: int | None = None
    protein_target: int | None = None
    is_within_range: bool = True
    deviations: list[dict[str, Any]] = []


class ExplanationBlock(BaseModel):
    constraints_applied: list[dict[str, Any]]
    scoring_weights: dict[str, str]
    generation_version: str = "1.0"
    catalog_version: str = "1.0"
    share_approximate_nutrients: float = 0.0
    statement: str = (
        "This plan is generated using deterministic scoring heuristics and is not guaranteed optimal or medically tailored."
    )


class MealPlanResponse(BaseModel):
    id: UUID
    name: str
    start_date: date
    end_date: date
    status: str
    generation_version: str
    target_snapshot: dict[str, Any] | None
    meals: list[PlannedMealResponse]
    days: list[DayNutrientTotal]
    warnings: list[dict[str, Any]]
    explanation: ExplanationBlock
    disclaimer: str


class SubstitutionSuggestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meal_id: UUID


class NutrientDifference(BaseModel):
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal


class SubstitutionOptionResponse(BaseModel):
    recipe_id: UUID
    recipe_name: str
    cuisine_code: str
    total_minutes: int
    servings: Decimal
    score: Decimal
    nutrients: MealNutrientSummary
    nutrient_diff: NutrientDifference


class SubstitutionAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meal_id: UUID
    recipe_id: UUID
    servings: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0.5"), le=Decimal("10.0"))


class MealEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    servings: Decimal | None = Field(default=None, ge=Decimal("0.5"), le=Decimal("10.0"))
    recipe_id: UUID | None = None


class GroceryItemResponse(BaseModel):
    name: str
    total_quantity: Decimal
    canonical_unit: str
    unit_family: str
    display_quantity: str
    food_id: UUID | None = None
    category: str = "general"
    is_text_only: bool = False


class GroceryListResponse(BaseModel):
    plan_id: UUID
    from_date: date | None
    to_date: date | None
    items: list[GroceryItemResponse]
