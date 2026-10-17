"""Authentication and user schemas (spec SEC1, SEC8, AC-01, AC-02, AC-09)."""

import re
import uuid

from pydantic import Field, field_validator

from app.schemas.base import StrictSchema

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class RegisterRequest(StrictSchema):
    """Account registration payload (AC-01, AC-02, AC-09)."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(default="", max_length=100)

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not EMAIL_REGEX.match(trimmed):
            raise ValueError("Invalid email address format")
        return trimmed


class LoginRequest(StrictSchema):
    """Account login payload (AC-03, AC-09)."""

    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not EMAIL_REGEX.match(trimmed):
            raise ValueError("Invalid email address format")
        return trimmed


class UserResponse(StrictSchema):
    """Public user response entity."""

    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
