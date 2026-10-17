"""Pydantic schemas for exercises, foods, and recipes catalogue (spec §6, AC-49, AC-52, AC-53)."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field, computed_field

from app.schemas.base import StrictSchema


class ExerciseCreateRequest(StrictSchema):
    name: str = Field(..., min_length=1, max_length=100)
    primary_muscle: str = Field(..., min_length=1, max_length=50)
    equipment: str = Field(..., min_length=1, max_length=50)
    movement_pattern: str = Field(default="", max_length=50)
    instructions: str | None = Field(default=None, max_length=1000)


class ExerciseResponse(StrictSchema):
    id: uuid.UUID
    name: str
    primary_muscle: str
    equipment: str
    movement_pattern: str
    instructions: str | None = None
    is_custom: bool


class FoodNutrientSchema(StrictSchema):
    nutrient_code: str
    amount_per_100g: Decimal
    unit: str


class FoodResponse(StrictSchema):
    id: uuid.UUID
    name: str
    food_category: str
    cuisine_code: str | None = None
    serving_description: str
    default_serving_g: Decimal | None = None
    state: str
    approximate: bool
    allergens_verified: bool
    data_source: str
    source_reference: str | None = None
    verified_at: date | None = None
    nutrients: list[FoodNutrientSchema] = []
    allergens: list[str] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_approximate(self) -> bool:
        """Label approximate foods clearly in API responses (AC-49)."""
        return self.approximate


class RecipeIngredientResponse(StrictSchema):
    id: uuid.UUID
    food_id: uuid.UUID | None = None
    ingredient_name: str
    quantity: Decimal
    unit: str
    edible_weight_g: Decimal | None = None


class RecipeNutritionResponse(StrictSchema):
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal = Decimal("0")


class RecipeResponse(StrictSchema):
    id: uuid.UUID
    name: str
    cuisine_code: str
    instructions: str
    prep_minutes: int
    cook_minutes: int
    total_minutes: int
    servings: Decimal
    cost_minor_per_serving: int | None = None
    cost_currency: str = "INR"
    diet_tags: list[str] = []
    meal_types: list[str] = []
    ingredients: list[RecipeIngredientResponse] = []
    per_serving_nutrients: RecipeNutritionResponse
    allergens: list[str] = []
    has_incomplete_allergen_data: bool
