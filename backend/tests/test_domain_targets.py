"""Tests for nutrition targets calculation domain functions.

AC-19 (S4):
Male, 80 kg, 180 cm, age 25, moderate activity, build_strength:
BMR 1,805, TDEE 2,797.75, plus 5% = 2,937.64, rounded to 2,940 kcal;
protein 128 g (1.6 × 80); fat 82 g (25% of 2,940 kcal ÷ 9);
carbohydrate 423 g (the remaining 1,693 kcal ÷ 4).
Response lists formula, activity factor, goal adjustment, protein and fat assumptions.

AC-20 (S4):
Same inputs with sex_for_estimate = unspecified use s = −78:
BMR 1,722, TDEE 2,669.1, plus 5% = 2,802.56, rounded to 2,800 kcal,
and the assumption is shown.

AC-21 (S5):
Female, 45 kg, 160 cm, age 30, sedentary, maintain:
BMR 1,139, TDEE 1,366.8. Estimate endpoint returns estimate_below_floor,
saves no target, tells user to enter manually or seek guidance.
"""

from decimal import Decimal

from app.domain.targets import (
    calculate_bmr,
    calculate_macro_defaults,
    calculate_target_estimate,
    calculate_tdee,
)


def test_ac_19_male_target_estimate():
    # Male, 80 kg, 180 cm, age 25
    bmr = calculate_bmr(
        weight_kg=Decimal("80"),
        height_cm=Decimal("180"),
        age=25,
        sex="male",
    )
    assert bmr == Decimal("1805")

    # Moderate activity: 1.55
    tdee = calculate_tdee(bmr=bmr, activity_level="moderate")
    assert tdee == Decimal("2797.75")

    # Target estimate with build_strength (+5%)
    result = calculate_target_estimate(
        weight_kg=Decimal("80"),
        height_cm=Decimal("180"),
        age=25,
        sex="male",
        activity_level="moderate",
        goal="build_strength",
        estimate_floor_kcal=Decimal("1500"),
    )

    assert result.bmr == Decimal("1805")
    assert result.tdee == Decimal("2797.75")
    assert result.raw_calories == Decimal("2937.6375")
    assert result.calories == 2940
    assert result.protein_g == 128
    assert result.fat_g == 82
    assert result.carbs_g == 423
    assert result.is_below_floor is False

    # Check assumptions documented
    assert "Mifflin-St Jeor" in result.assumptions["formula"]
    assert result.assumptions["activity_factor"] == Decimal("1.55")
    assert result.assumptions["goal_factor"] == Decimal("1.05")
    assert result.assumptions["protein_g_per_kg"] == Decimal("1.6")
    assert result.assumptions["fat_pct_calories"] == Decimal("0.25")


def test_ac_20_unspecified_sex_target_estimate():
    # Same inputs with sex_for_estimate = unspecified
    result = calculate_target_estimate(
        weight_kg=Decimal("80"),
        height_cm=Decimal("180"),
        age=25,
        sex="unspecified",
        activity_level="moderate",
        goal="build_strength",
        estimate_floor_kcal=Decimal("1500"),
    )

    # s = -78
    assert result.bmr == Decimal("1722")
    assert result.tdee == Decimal("2669.1")
    assert result.calories == 2800
    assert result.assumptions["sex_factor_s"] == Decimal("-78")


def test_ac_21_below_floor_detection():
    # Female, 45 kg, 160 cm, age 30, sedentary, maintain
    bmr = calculate_bmr(
        weight_kg=Decimal("45"),
        height_cm=Decimal("160"),
        age=30,
        sex="female",
    )
    assert bmr == Decimal("1139")

    tdee = calculate_tdee(bmr=bmr, activity_level="sedentary")
    assert tdee == Decimal("1366.8")

    result = calculate_target_estimate(
        weight_kg=Decimal("45"),
        height_cm=Decimal("160"),
        age=30,
        sex="female",
        activity_level="sedentary",
        goal="maintain",
        estimate_floor_kcal=Decimal("1500"),
    )

    assert result.is_below_floor is True
    assert result.calories == 1370
    assert result.floor_threshold == Decimal("1500")


def test_macro_defaults_standalone():
    # Test macro defaults directly with exact numbers from spec §5.4
    macros = calculate_macro_defaults(
        calories=2940,
        weight_kg=Decimal("80"),
        protein_g_per_kg=Decimal("1.6"),
        fat_pct=Decimal("0.25"),
    )
    assert macros["protein_g"] == 128
    assert macros["fat_g"] == 82
    assert macros["carbs_g"] == 423
