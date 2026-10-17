"""Tests for profile validation (spec §6, FR-01, AC-15)."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.profile import ProfileUpdateRequest


def test_ac_15_valid_profile_update():
    # Valid values should pass cleanly
    p = ProfileUpdateRequest(
        height_cm=Decimal("175.5"),
        body_weight_kg=Decimal("72.0"),
        timezone="Asia/Kolkata",
        units="kg",
        goal="build_strength",
    )
    assert p.height_cm == Decimal("175.5")
    assert p.timezone == "Asia/Kolkata"
    assert p.units == "kg"


def test_ac_15_height_outside_range_rejected():
    # Height outside 50 to 260 cm rejected with 422
    with pytest.raises(ValidationError) as exc_info:
        ProfileUpdateRequest(height_cm=Decimal("49.9"))
    errors = exc_info.value.errors()
    assert any("height_cm" in loc for loc in [e["loc"] for e in errors])

    with pytest.raises(ValidationError) as exc_info:
        ProfileUpdateRequest(height_cm=Decimal("260.1"))
    errors = exc_info.value.errors()
    assert any("height_cm" in loc for loc in [e["loc"] for e in errors])


def test_ac_15_weight_outside_range_rejected():
    # Weight outside 20 to 400 kg rejected with 422
    with pytest.raises(ValidationError) as exc_info:
        ProfileUpdateRequest(body_weight_kg=Decimal("19.9"))
    errors = exc_info.value.errors()
    assert any("body_weight_kg" in loc for loc in [e["loc"] for e in errors])

    with pytest.raises(ValidationError) as exc_info:
        ProfileUpdateRequest(body_weight_kg=Decimal("400.1"))
    errors = exc_info.value.errors()
    assert any("body_weight_kg" in loc for loc in [e["loc"] for e in errors])


def test_ac_15_invalid_timezone_rejected():
    # Invalid IANA timezone rejected with 422 and field name
    with pytest.raises(ValidationError) as exc_info:
        ProfileUpdateRequest(timezone="Invalid/NonExistent_Zone")
    errors = exc_info.value.errors()
    assert any("timezone" in loc for loc in [e["loc"] for e in errors])


def test_ac_15_invalid_units_rejected():
    # Units other than 'kg' or 'lb' rejected with 422 and field name
    with pytest.raises(ValidationError) as exc_info:
        ProfileUpdateRequest(units="stone")  # type: ignore[arg-type]
    errors = exc_info.value.errors()
    assert any("units" in loc for loc in [e["loc"] for e in errors])
