"""Pydantic schemas for nutrition targets, estimation, preferences, and safety rules (spec §5.4, §7, S2–S7)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from app.schemas.base import StrictSchema


class NutritionGoalCreate(StrictSchema):
    calorie_target_kcal: int | None = Field(
        default=None,
        gt=0,
        description="Daily calorie target (must be > 0 if provided)",
    )
    protein_target_g: int | None = Field(default=None, ge=0)
    carbs_target_g: int | None = Field(default=None, ge=0)
    fat_target_g: int | None = Field(default=None, ge=0)
    effective_from: date | None = Field(
        default=None,
        description="Date from which this target applies (defaults to today in user timezone)",
    )
    rationale: str | None = Field(default=None, max_length=1000)


class NutritionGoalResponse(StrictSchema):
    id: str
    effective_from: str
    calorie_target_kcal: int | None = None
    protein_target_g: int | None = None
    carbs_target_g: int | None = None
    fat_target_g: int | None = None
    rationale: str | None = None
    warning: str | None = None
    created_at: datetime
    disclaimer: str = (
        "Estimates are informational and not medical advice, and this app is not a substitute for a registered dietitian or doctor."
    )


class NutritionEstimateRequest(StrictSchema):
    weight_kg: Decimal | None = Field(default=None, ge=Decimal("20.0"), le=Decimal("400.0"))
    height_cm: Decimal | None = Field(default=None, ge=Decimal("50.0"), le=Decimal("260.0"))
    age: int | None = Field(default=None, ge=18, le=120)
    sex_for_estimate: Literal["male", "female", "unspecified"] | None = None
    activity_level: Literal["sedentary", "light", "moderate", "very_active"] | None = None
    goal: Literal["maintain", "build_strength", "build_muscle"] | None = None
    save_as_active: bool = False


class NutritionEstimateResponse(StrictSchema):
    status: Literal["ok", "estimate_below_floor"]
    calories: int | None = None
    protein_g: int | None = None
    fat_g: int | None = None
    carbs_g: int | None = None
    bmr: str | None = None
    tdee: str | None = None
    formula: str
    activity_factor: str
    goal_adjustment: str
    protein_assumption: str
    fat_assumption: str
    assumptions: dict[str, Any]
    warning: str | None = None
    requires_professional_guidance: bool = False
    disclaimer: str = (
        "Estimates are informational and not medical advice, and this app is not a substitute for a registered dietitian or doctor."
    )


class FoodConstraintItem(StrictSchema):
    constraint_type: Literal["allergy", "diet_tag", "excluded_ingredient"]
    value: str = Field(..., min_length=1, max_length=100)


class UserPreferencesUpdate(StrictSchema):
    allergies: list[str] | None = None
    diet_tags: list[str] | None = None
    excluded_ingredients: list[str] | None = None
    cuisine_preferences: dict[str, Literal["preferred", "like", "neutral", "avoid"]] | None = None
    max_minutes_per_meal: int | None = Field(default=None, ge=0)
    daily_budget: Decimal | None = Field(default=None, ge=Decimal("0.0"))
    exclude_unverified_allergens: bool | None = None


class UserPreferencesResponse(StrictSchema):
    allergies: list[str]
    diet_tags: list[str]
    excluded_ingredients: list[str]
    cuisine_preferences: dict[str, str]
    max_minutes_per_meal: int | None
    daily_budget: str | None
    exclude_unverified_allergens: bool
    disclaimer: str = (
        "Estimates are informational and not medical advice, and this app is not a substitute for a registered dietitian or doctor."
    )
