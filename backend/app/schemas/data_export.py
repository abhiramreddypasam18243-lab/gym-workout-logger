"""Pydantic schemas and JSON Schema definition for user data export (spec §6, FR-15, AC-88)."""

from typing import Any
from pydantic import BaseModel, Field


class UserExportData(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: str


class ProfileExportData(BaseModel):
    user_id: str
    display_name: str
    birth_date: str | None = None
    height_cm: str | None = None
    body_weight_kg: str | None = None
    timezone: str
    units: str
    sex_for_estimate: str
    adult_confirmed_at: str | None = None
    needs_professional_guidance: bool
    calories_hidden: bool
    nutrition_paused: bool
    track_body_weight: bool
    weekly_session_target: int | None = None
    currency_code: str
    goal: str
    activity_level: str


class FoodConstraintExportData(BaseModel):
    id: str
    constraint_type: str
    constraint_value: str
    is_hard_constraint: bool


class CuisinePreferenceExportData(BaseModel):
    id: str
    cuisine_code: str
    preference_level: str


class NutritionGoalExportData(BaseModel):
    id: str
    effective_from: str
    calorie_target_kcal: int | None = None
    protein_target_g: int | None = None
    carbs_target_g: int | None = None
    fat_target_g: int | None = None
    rationale: str | None = None
    created_at: str


class RoutineExerciseExportData(BaseModel):
    exercise_id: str
    order_index: int
    target_sets: int
    rep_min: int
    rep_max: int
    notes: str | None = None


class RoutineExportData(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: str
    exercises: list[RoutineExerciseExportData] = Field(default_factory=list)


class WorkoutSetExportData(BaseModel):
    id: str
    set_number: int
    reps: int
    load_kg: str
    rpe: str | None = None
    is_warmup: bool
    completed_at: str | None = None


class WorkoutExerciseExportData(BaseModel):
    id: str
    exercise_id: str
    order_index: int
    notes: str | None = None
    sets: list[WorkoutSetExportData] = Field(default_factory=list)


class WorkoutSessionExportData(BaseModel):
    id: str
    routine_id: str | None = None
    started_at: str
    completed_at: str | None = None
    notes: str | None = None
    exercises: list[WorkoutExerciseExportData] = Field(default_factory=list)


class CustomExerciseExportData(BaseModel):
    id: str
    name: str
    primary_muscle: str
    equipment: str
    movement_pattern: str = ""
    instructions: str | None = None


class PlannedMealItemExportData(BaseModel):
    id: str
    food_id: str | None = None
    recipe_id: str | None = None
    quantity: str
    unit: str
    nutrient_snapshot: dict[str, Any] | None = None


class PlannedMealExportData(BaseModel):
    id: str
    plan_date: str
    meal_type: str
    title: str
    recipe_id: str | None = None
    servings: str
    sort_order: int = 0
    items: list[PlannedMealItemExportData] = Field(default_factory=list)


class MealPlanExportData(BaseModel):
    id: str
    start_date: str
    end_date: str
    status: str
    created_at: str
    planned_meals: list[PlannedMealExportData] = Field(default_factory=list)


class NutritionLogItemExportData(BaseModel):
    id: str
    food_id: str | None = None
    recipe_id: str | None = None
    quantity: str
    unit: str
    nutrient_snapshot: dict[str, Any] | None = None


class NutritionLogExportData(BaseModel):
    id: str
    consumed_at: str
    meal_type: str
    source_type: str = "food"
    notes: str | None = None
    items: list[NutritionLogItemExportData] = Field(default_factory=list)


class ExportMetadata(BaseModel):
    export_version: str = "1.0"
    user_id: str
    exported_at: str
    record_counts: dict[str, int]


class CompleteUserDataExport(BaseModel):
    metadata: ExportMetadata
    user: UserExportData
    profile: ProfileExportData | None = None
    food_constraints: list[FoodConstraintExportData] = Field(default_factory=list)
    cuisine_preferences: list[CuisinePreferenceExportData] = Field(default_factory=list)
    nutrition_goals: list[NutritionGoalExportData] = Field(default_factory=list)
    routines: list[RoutineExportData] = Field(default_factory=list)
    workout_sessions: list[WorkoutSessionExportData] = Field(default_factory=list)
    custom_exercises: list[CustomExerciseExportData] = Field(default_factory=list)
    meal_plans: list[MealPlanExportData] = Field(default_factory=list)
    nutrition_logs: list[NutritionLogExportData] = Field(default_factory=list)


def get_export_json_schema() -> dict[str, Any]:
    """Return JSON schema for validating export documents."""
    return CompleteUserDataExport.model_json_schema()

