"""Tests for meal plan candidate scoring and serving size selection domain functions.

AC-63 (5.5):
Slot target 700 kcal and 40 g protein; a candidate at 650 kcal and 35 g protein,
a preferred cuisine (+1.0), total time 20 minutes, no budget, no repetition, s = 1:
target_fit = −(50/700 + 5/40)/2 = −0.09821,
score = −0.09821 + 0.3 − 0.2 × (20/60) = 0.1351.

AC-64 (5.5):
A recipe of 400 kcal per serving against a 700 kcal slot:
sizes 1.5 (600) and 2 (800) tie at a deviation of 100, so 1.5 is chosen;
1.75 is not an allowed size.
"""

from decimal import Decimal

from app.domain.scoring import (
    ALLOWED_SERVING_SIZES,
    calculate_candidate_score,
    calculate_target_fit,
    select_best_serving_size,
)


def test_ac_63_scoring_example():
    # Slot target 700 kcal and 40 g protein
    slot_kcal = Decimal("700")
    slot_protein = Decimal("40")

    # Candidate at 650 kcal and 35 g protein (at s=1)
    cand_kcal = Decimal("650")
    cand_protein = Decimal("35")

    # target_fit = -( |650 - 700| / 700 + |35 - 40| / 40 ) / 2
    # = -( 50/700 + 5/40 ) / 2
    # 50/700 = 1/14 = 0.07142857...
    # 5/40 = 1/8 = 0.125
    # sum = 0.19642857... / 2 = 0.09821428...
    # target_fit = -0.09821428...
    target_fit = calculate_target_fit(
        cand_kcal=cand_kcal,
        cand_protein=cand_protein,
        slot_kcal=slot_kcal,
        slot_protein=slot_protein,
    )
    # Check intermediate target_fit to 5 decimal places: -0.09821
    assert round(float(target_fit), 5) == -0.09821

    # Candidate score with preferred cuisine (+1.0), total_minutes=20, no budget, no repetition
    score = calculate_candidate_score(
        target_fit=target_fit,
        cuisine_match=Decimal("1.0"),
        total_minutes=20,
        budget_ratio=Decimal("0"),
        repetition=0,
    )

    # score = 1.0 * (-0.09821) + 0.3 * 1.0 - 0.2 * (20/60) = 0.135119...
    assert round(float(score), 4) == 0.1351


def test_ac_64_serving_size_selection():
    # Recipe has 400 kcal per serving
    recipe_kcal_per_serving = Decimal("400")
    slot_kcal = Decimal("700")

    # Test allowed sizes
    assert (
        Decimal("0.5"),
        Decimal("1.0"),
        Decimal("1.5"),
        Decimal("2.0"),
        Decimal("2.5"),
        Decimal("3.0"),
    ) == ALLOWED_SERVING_SIZES
    assert Decimal("1.75") not in ALLOWED_SERVING_SIZES

    # At 1.5 servings: 600 kcal, deviation = |600 - 700| = 100
    # At 2.0 servings: 800 kcal, deviation = |800 - 700| = 100
    # Ties go to the smaller size: 1.5 is chosen
    best_size = select_best_serving_size(
        recipe_kcal_per_serving=recipe_kcal_per_serving,
        slot_kcal=slot_kcal,
    )
    assert best_size == Decimal("1.5")
