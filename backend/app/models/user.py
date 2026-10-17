"""User, session, profile, and constraint models (spec §6, SEC1, SEC2, S2, S3, S7, AC-01–05, AC-15)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.nutrition import MealPlan, NutritionGoal, NutritionLog, Recipe
    from app.models.workout import Exercise, WorkoutRoutine, WorkoutSession


class User(Base):
    """User account entity (spec §6, FR-01, SEC1)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    food_constraints: Mapped[list["UserFoodConstraint"]] = relationship(
        "UserFoodConstraint", back_populates="user", cascade="all, delete-orphan"
    )
    cuisine_preferences: Mapped[list["UserCuisinePreference"]] = relationship(
        "UserCuisinePreference", back_populates="user", cascade="all, delete-orphan"
    )
    routines: Mapped[list["WorkoutRoutine"]] = relationship(
        "WorkoutRoutine", back_populates="user", cascade="all, delete-orphan"
    )
    workout_sessions: Mapped[list["WorkoutSession"]] = relationship(
        "WorkoutSession", back_populates="user", cascade="all, delete-orphan"
    )
    custom_exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise", back_populates="owner", cascade="all, delete-orphan"
    )
    custom_recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe", back_populates="owner", cascade="all, delete-orphan"
    )
    nutrition_goals: Mapped[list["NutritionGoal"]] = relationship(
        "NutritionGoal", back_populates="user", cascade="all, delete-orphan"
    )
    meal_plans: Mapped[list["MealPlan"]] = relationship(
        "MealPlan", back_populates="user", cascade="all, delete-orphan"
    )
    nutrition_logs: Mapped[list["NutritionLog"]] = relationship(
        "NutritionLog", back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    """Server-side revocable session entity (spec §6, SEC2, AC-03–05)."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class UserProfile(Base):
    """User profile and safety settings (spec §6, S2, S3, S7, AC-15)."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint("height_cm >= 50 AND height_cm <= 260", name="chk_profile_height"),
        CheckConstraint(
            "body_weight_kg >= 20 AND body_weight_kg <= 400", name="chk_profile_weight"
        ),
        CheckConstraint("units IN ('kg', 'lb')", name="chk_profile_units"),
        CheckConstraint("goal IN ('maintain', 'build_strength')", name="chk_profile_goal"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    body_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    units: Mapped[str] = mapped_column(String(2), default="kg", nullable=False)
    sex_for_estimate: Mapped[str] = mapped_column(String(20), default="unspecified", nullable=False)
    adult_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    needs_professional_guidance: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    calories_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nutrition_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    track_body_weight: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weekly_session_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    goal: Mapped[str] = mapped_column(String(30), default="maintain", nullable=False)
    activity_level: Mapped[str] = mapped_column(String(30), default="moderate", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")


class UserFoodConstraint(Base):
    """User dietary restrictions and allergies (spec §6, S9, AC-57–59)."""

    __tablename__ = "user_food_constraints"
    __table_args__ = (
        CheckConstraint(
            "constraint_type IN ('allergy', 'diet_tag', 'excluded_ingredient')",
            name="chk_constraint_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    constraint_type: Mapped[str] = mapped_column(String(30), nullable=False)
    constraint_value: Mapped[str] = mapped_column(String(100), nullable=False)
    is_hard_constraint: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="food_constraints")


class UserCuisinePreference(Base):
    """User multi-cuisine preferences with ranking levels (spec §6, FR-06, AC-61)."""

    __tablename__ = "user_cuisine_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "cuisine_code", name="uq_user_cuisine"),
        CheckConstraint(
            "preference_level IN ('preferred', 'like', 'neutral', 'avoid')",
            name="chk_preference_level",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cuisine_code: Mapped[str] = mapped_column(String(50), nullable=False)
    preference_level: Mapped[str] = mapped_column(String(20), default="neutral", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="cuisine_preferences")
