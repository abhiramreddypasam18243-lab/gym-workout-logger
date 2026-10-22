"""Schemas for weekly set targets per muscle group (D-34, AC-125)."""

from typing import Annotated

from pydantic import Field

from app.schemas.base import StrictSchema


class MuscleSetTargetsUpdate(StrictSchema):
    # muscle group -> working sets per week; an empty object clears every target
    targets: dict[Annotated[str, Field(min_length=1, max_length=50)], Annotated[int, Field(ge=1, le=40)]] = Field(
        ..., max_length=20
    )
