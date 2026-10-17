"""Tests for unit conversion domain functions.

AC-16 (5.1):
100 lb converts to 45.359237 kg exactly, 1 kg to 2.2046226218 lb,
a round trip returns the original within 1e-9, and storage is always in kg.
"""

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from app.domain.units import (
    VOLUME_FACTORS_ML,
    cup_to_ml,
    format_weight,
    kg_to_lb,
    lb_to_kg,
    tbsp_to_ml,
    tsp_to_ml,
)


def test_ac_16_lb_to_kg_exact():
    # 100 lb converts to 45.359237 kg exactly
    result = lb_to_kg(Decimal("100"))
    assert result == Decimal("45.359237")


def test_ac_16_kg_to_lb():
    # 1 kg to 2.2046226218 lb (within 1e-9 precision)
    result = kg_to_lb(Decimal("1"))
    expected = Decimal("2.2046226218")
    assert abs(result - expected) <= Decimal("0.0000000001")


def test_ac_16_round_trip():
    # Round trip returns the original within 1e-9
    original_kg = Decimal("75.5")
    reconverted = lb_to_kg(kg_to_lb(original_kg))
    assert abs(reconverted - original_kg) <= Decimal("1e-9")


@given(st.decimals(min_value=Decimal("0.1"), max_value=Decimal("500.0"), places=2))
def test_ac_16_round_trip_property(kg_val: Decimal):
    # Property-based round trip test for any weight in normal range
    reconverted = lb_to_kg(kg_to_lb(kg_val))
    assert abs(reconverted - kg_val) <= Decimal("1e-9")


def test_ac_16_volume_units():
    # D-15: 1 tsp = 5 ml, 1 tbsp = 15 ml, 1 cup = 240 ml
    assert tsp_to_ml(Decimal("1")) == Decimal("5")
    assert tbsp_to_ml(Decimal("1")) == Decimal("15")
    assert cup_to_ml(Decimal("1")) == Decimal("240")
    assert VOLUME_FACTORS_ML["tsp"] == Decimal("5")
    assert VOLUME_FACTORS_ML["tbsp"] == Decimal("15")
    assert VOLUME_FACTORS_ML["cup"] == Decimal("240")


def test_ac_16_format_weight_display():
    # Display rounding: 1 decimal place (half-up)
    assert format_weight(Decimal("93.33"), "kg") == "93.3 kg"
    # 100 kg to lb display
    lb_val = kg_to_lb(Decimal("100"))
    assert format_weight(lb_val, "lb") == "220.5 lb"
