"""User profile schemas with range and IANA timezone validation (spec §6, AC-15)."""

import zoneinfo
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import StrictSchema


class ProfileUpdateRequest(StrictSchema):
    """User profile update request with validation for AC-15."""

    display_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    height_cm: Decimal | None = Field(default=None, ge=Decimal("50.0"), le=Decimal("260.0"))
    body_weight_kg: Decimal | None = Field(default=None, ge=Decimal("20.0"), le=Decimal("400.0"))
    timezone: str | None = None
    units: Literal["kg", "lb"] | None = None
    sex_for_estimate: Literal["male", "female", "unspecified"] | None = None
    needs_professional_guidance: bool | None = None
    calories_hidden: bool | None = None
    nutrition_paused: bool | None = None
    track_body_weight: bool | None = None
    weekly_session_target: int | None = Field(default=None, ge=0, le=21)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    goal: Literal["maintain", "build_strength", "build_muscle"] | None = None
    activity_level: Literal["sedentary", "light", "moderate", "very_active"] | None = None

    @field_validator("timezone")
    @classmethod
    def validate_iana_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        # Check standard zoneinfo
        try:
            zoneinfo.ZoneInfo(v)
            return v
        except Exception:
            raise ValueError(f"Invalid IANA timezone: '{v}'") from None


class ProfileResponse(StrictSchema):
    """User profile response."""

    user_id: str
    display_name: str
    birth_date: date | None
    height_cm: Decimal | None
    body_weight_kg: Decimal | None
    timezone: str
    units: str
    sex_for_estimate: str
    adult_confirmed_at: str | None
    needs_professional_guidance: bool
    calories_hidden: bool
    nutrition_paused: bool
    track_body_weight: bool
    weekly_session_target: int | None
    currency_code: str
    goal: str
    activity_level: str
