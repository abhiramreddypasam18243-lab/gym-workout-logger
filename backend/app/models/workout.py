"""Workout, routine, exercise, and set models (spec §6, FR-02, FR-03, FR-04, AC-29–38)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Exercise(Base):
    """Exercise catalogue item (spec §6, FR-02, AC-29, AC-30)."""

    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    primary_muscle: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    equipment: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    movement_pattern: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    owner: Mapped[Optional["User"]] = relationship("User", back_populates="custom_exercises")


class WorkoutRoutine(Base):
    """Reusable workout routine template (spec §6, FR-04, AC-35)."""

    __tablename__ = "workout_routines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="routines")
    exercises: Mapped[list["RoutineExercise"]] = relationship(
        "RoutineExercise",
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.order_index",
    )


class RoutineExercise(Base):
    """Target exercise within a routine (spec §6, FR-04, AC-35)."""

    __tablename__ = "routine_exercises"
    __table_args__ = (
        CheckConstraint("rep_min <= rep_max", name="chk_routine_rep_range"),
        CheckConstraint("target_sets > 0", name="chk_routine_target_sets"),
        CheckConstraint("rep_min > 0", name="chk_routine_rep_min"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    routine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workout_routines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    target_sets: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    rep_min: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    rep_max: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    routine: Mapped["WorkoutRoutine"] = relationship("WorkoutRoutine", back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship("Exercise")


class WorkoutSession(Base):
    """A logged training session (spec §6, FR-03, AC-31–38)."""

    __tablename__ = "workout_sessions"
    __table_args__ = (Index("idx_workout_sessions_user_started", "user_id", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    routine_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workout_routines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="workout_sessions")
    routine: Mapped[Optional["WorkoutRoutine"]] = relationship("WorkoutRoutine")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        "WorkoutExercise",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.order_index",
    )


class WorkoutExercise(Base):
    """Exercise performed within a workout session (spec §6, FR-03)."""

    __tablename__ = "workout_exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["WorkoutSession"] = relationship("WorkoutSession", back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship("Exercise")
    sets: Mapped[list["WorkoutSet"]] = relationship(
        "WorkoutSet",
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_number",
    )


class WorkoutSet(Base):
    """Individual set performance record (spec §6, FR-03, AC-32)."""

    __tablename__ = "workout_sets"
    __table_args__ = (
        UniqueConstraint("workout_exercise_id", "set_number", name="uq_exercise_set_number"),
        CheckConstraint("reps > 0", name="chk_set_reps_positive"),
        CheckConstraint("load_kg >= 0", name="chk_set_load_non_negative"),
        CheckConstraint("rpe IS NULL OR (rpe >= 1.0 AND rpe <= 10.0)", name="chk_set_rpe_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workout_exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workout_exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    load_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    workout_exercise: Mapped["WorkoutExercise"] = relationship(
        "WorkoutExercise", back_populates="sets"
    )


class MuscleSetTarget(Base):
    """A user's weekly working-set goal for one muscle group (D-34, AC-125)."""

    __tablename__ = "muscle_set_targets"
    __table_args__ = (
        UniqueConstraint("user_id", "muscle", name="uq_muscle_set_target_user_muscle"),
        CheckConstraint("weekly_sets BETWEEN 1 AND 40", name="chk_muscle_set_target_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    muscle: Mapped[str] = mapped_column(String(50), nullable=False)
    weekly_sets: Mapped[int] = mapped_column(Integer, nullable=False)
