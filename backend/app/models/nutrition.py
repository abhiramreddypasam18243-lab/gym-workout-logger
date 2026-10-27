"""Nutrition catalogue, recipe, goal, meal plan, and intake log models (spec §6, DL1–4, S9, FR-06–12)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Food(Base):
    """Food catalogue item with provenance (spec §6, DL1, DL4, AC-49, AC-50)."""

    __tablename__ = "foods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    food_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cuisine_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    serving_description: Mapped[str] = mapped_column(String(100), nullable=False)
    default_serving_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="raw", nullable=False)
    approximate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allergens_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    verified_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # NULL = reviewed catalogue food; set = a custom food only its owner can see (D-32)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    nutrients: Mapped[list["FoodNutrient"]] = relationship(
        "FoodNutrient", back_populates="food", cascade="all, delete-orphan"
    )
    allergens: Mapped[list["FoodAllergen"]] = relationship(
        "FoodAllergen", back_populates="food", cascade="all, delete-orphan"
    )


class FoodNutrient(Base):
    """Per-100g nutrient facts for a food (spec §6, DL1, AC-45, AC-48)."""

    __tablename__ = "food_nutrients"
    __table_args__ = (
        CheckConstraint("amount_per_100g >= 0", name="chk_nutrient_amount_non_negative"),
    )

    food_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("foods.id", ondelete="CASCADE"), primary_key=True
    )
    nutrient_code: Mapped[str] = mapped_column(String(30), primary_key=True)
    amount_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), default="g", nullable=False)

    food: Mapped["Food"] = relationship("Food", back_populates="nutrients")


class FoodAllergen(Base):
    """EU-14 allergen association for a food (spec §6, S9, AC-52)."""

    __tablename__ = "food_allergens"

    food_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("foods.id", ondelete="CASCADE"), primary_key=True
    )
    allergen_code: Mapped[str] = mapped_column(String(50), primary_key=True)

    food: Mapped["Food"] = relationship("Food", back_populates="allergens")


class Recipe(Base):
    """Curated or user-created recipe (spec §6, DL3, AC-51)."""

    __tablename__ = "recipes"
    __table_args__ = (
        CheckConstraint("prep_minutes >= 0", name="chk_recipe_prep_time"),
        CheckConstraint("cook_minutes >= 0", name="chk_recipe_cook_time"),
        CheckConstraint("servings > 0", name="chk_recipe_servings_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    cuisine_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    prep_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cook_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    servings: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=1.0, nullable=False)
    cost_minor_per_serving: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    owner: Mapped[Optional["User"]] = relationship("User", back_populates="custom_recipes")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    diet_tags: Mapped[list["RecipeDietTag"]] = relationship(
        "RecipeDietTag", back_populates="recipe", cascade="all, delete-orphan"
    )
    meal_types: Mapped[list["RecipeMealType"]] = relationship(
        "RecipeMealType", back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeIngredient(Base):
    """Ingredient in a recipe (spec §6, AC-46, AC-79)."""

    __tablename__ = "recipe_ingredients"
    __table_args__ = (CheckConstraint("quantity > 0", name="chk_ingredient_qty_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("foods.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    ingredient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    edible_weight_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")
    food: Mapped[Optional["Food"]] = relationship("Food")


class RecipeDietTag(Base):
    """Normalized diet tags for a recipe (spec §6, AC-59)."""

    __tablename__ = "recipe_diet_tags"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    diet_tag: Mapped[str] = mapped_column(String(50), primary_key=True)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="diet_tags")


class RecipeMealType(Base):
    """Allowed meal slots for a recipe (spec §6, AC-60)."""

    __tablename__ = "recipe_meal_types"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True
    )
    meal_type: Mapped[str] = mapped_column(String(30), primary_key=True)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="meal_types")


class NutritionGoal(Base):
    """Versioned user nutrition targets (spec §6, FR-07, AC-23)."""

    __tablename__ = "nutrition_goals"
    __table_args__ = (
        Index("idx_nutrition_goals_user_date", "user_id", "effective_from"),
        CheckConstraint(
            "calorie_target_kcal IS NULL OR calorie_target_kcal > 0",
            name="chk_target_calories_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    calorie_target_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protein_target_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carbs_target_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fat_target_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="nutrition_goals")


class MealPlan(Base):
    """Generated 7-day meal plan with target snapshot (spec §6, FR-08, AC-56–72)."""

    __tablename__ = "meal_plans"
    __table_args__ = (Index("idx_meal_plans_user_start", "user_id", "start_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), default="7-Day Meal Plan", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ok", nullable=False)
    generation_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    target_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="meal_plans")
    meals: Mapped[list["PlannedMeal"]] = relationship(
        "PlannedMeal",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlannedMeal.plan_date, PlannedMeal.sort_order",
    )


class PlannedMeal(Base):
    """Specific meal slot within a meal plan (spec §6, FR-08)."""

    __tablename__ = "planned_meals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meal_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    servings: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=1.0, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    plan: Mapped["MealPlan"] = relationship("MealPlan", back_populates="meals")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")
    items: Mapped[list["PlannedMealItem"]] = relationship(
        "PlannedMealItem", back_populates="meal", cascade="all, delete-orphan"
    )


class PlannedMealItem(Base):
    """Planned component with immutable historical nutrient snapshot (spec §6, AC-54)."""

    __tablename__ = "planned_meal_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    planned_meal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planned_meals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    food_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("foods.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    ingredient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    nutrient_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    meal: Mapped["PlannedMeal"] = relationship("PlannedMeal", back_populates="items")
    food: Mapped[Optional["Food"]] = relationship("Food")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")


class NutritionLog(Base):
    """Logged actual intake session (spec §6, FR-12, AC-82–84)."""

    __tablename__ = "nutrition_logs"
    __table_args__ = (Index("idx_nutrition_logs_user_consumed", "user_id", "consumed_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default="food", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="nutrition_logs")
    items: Mapped[list["NutritionLogItem"]] = relationship(
        "NutritionLogItem", back_populates="log", cascade="all, delete-orphan"
    )


class NutritionLogItem(Base):
    """Logged item with historical nutrient snapshot (spec §6, AC-54, AC-82)."""

    __tablename__ = "nutrition_log_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nutrition_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nutrition_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    food_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("foods.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    nutrient_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    log: Mapped["NutritionLog"] = relationship("NutritionLog", back_populates="items")
    food: Mapped[Optional["Food"]] = relationship("Food")
    recipe: Mapped[Optional["Recipe"]] = relationship("Recipe")
