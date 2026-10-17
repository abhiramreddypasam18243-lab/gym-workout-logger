"""Pydantic schemas for workouts, routines, exercises, and sets (spec §6, FR-03, FR-04, AC-31–38)."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from app.schemas.base import StrictSchema


class RoutineExerciseCreate(StrictSchema):
    exercise_id: uuid.UUID
    order_index: int = 0
    target_sets: int = Field(default=3, gt=0)
    rep_min: int = Field(default=8, gt=0)
    rep_max: int = Field(default=12, gt=0)
    rest_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_rep_range(self) -> "RoutineExerciseCreate":
        if self.rep_min > self.rep_max:
            raise ValueError(f"rep_min ({self.rep_min}) must be <= rep_max ({self.rep_max})")
        return self


class RoutineExerciseResponse(StrictSchema):
    id: uuid.UUID
    exercise_id: uuid.UUID
    exercise_name: str | None = None
    order_index: int
    target_sets: int
    rep_min: int
    rep_max: int
    rest_seconds: int | None = None


class RoutineCreateRequest(StrictSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    exercises: list[RoutineExerciseCreate] = []


class RoutineResponse(StrictSchema):
    id: uuid.UUID
    name: str
    description: str | None = None
    exercises: list[RoutineExerciseResponse] = []
    created_at: datetime
    updated_at: datetime


class WorkoutSetCreate(StrictSchema):
    set_number: int = Field(..., ge=1)
    reps: int = Field(..., gt=0, description="Reps must be strictly positive (AC-32)")
    load_kg: Decimal = Field(..., ge=Decimal("0"), description="Load cannot be negative (AC-32)")
    rpe: Decimal | None = Field(
        default=None,
        ge=Decimal("1.0"),
        le=Decimal("10.0"),
        description="RPE between 1.0 and 10.0 in steps of 0.5 (AC-32)",
    )
    is_warmup: bool = False
    completed_at: datetime

    @field_validator("rpe")
    @classmethod
    def validate_rpe_step(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and (v * Decimal("2")) % Decimal("1") != Decimal("0"):
            raise ValueError("RPE must be in steps of 0.5 (e.g. 7.0, 7.5, 8.0)")
        return v


class WorkoutSetResponse(StrictSchema):
    id: uuid.UUID
    set_number: int
    reps: int
    load_kg: Decimal
    rpe: Decimal | None = None
    is_warmup: bool
    completed_at: datetime


class WorkoutExerciseCreate(StrictSchema):
    exercise_id: uuid.UUID
    order_index: int = 0
    notes: str | None = Field(default=None, max_length=1000)
    sets: list[WorkoutSetCreate] = []

    @model_validator(mode="after")
    def validate_duplicate_set_numbers(self) -> "WorkoutExerciseCreate":
        set_nums = [s.set_number for s in self.sets]
        if len(set_nums) != len(set(set_nums)):
            raise ValueError("Duplicate set numbers are rejected within the same exercise (AC-32)")
        return self


class WorkoutExerciseResponse(StrictSchema):
    id: uuid.UUID
    exercise_id: uuid.UUID
    exercise_name: str | None = None
    order_index: int
    notes: str | None = None
    sets: list[WorkoutSetResponse] = []


class WorkoutSessionCreateRequest(StrictSchema):
    routine_id: uuid.UUID | None = None
    started_at: datetime
    completed_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)
    exercises: list[WorkoutExerciseCreate] = []

    @model_validator(mode="after")
    def validate_set_completion_times(self) -> "WorkoutSessionCreateRequest":
        for ex in self.exercises:
            for s in ex.sets:
                if s.completed_at < self.started_at:
                    raise ValueError(
                        f"Set {s.set_number} completed_at ({s.completed_at}) cannot be earlier than session start ({self.started_at})"
                    )
        return self


class WorkoutSessionResponse(StrictSchema):
    id: uuid.UUID
    routine_id: uuid.UUID | None = None
    started_at: datetime
    completed_at: datetime | None = None
    notes: str | None = None
    exercises: list[WorkoutExerciseResponse] = []


class WorkoutHistoryResponse(StrictSchema):
    items: list[WorkoutSessionResponse]
    next_cursor: str | None = None
