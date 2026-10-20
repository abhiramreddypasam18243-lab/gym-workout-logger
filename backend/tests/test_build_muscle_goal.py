"""AC-119 (D-29): the build_muscle goal adds +10% to TDEE; no deficit goal exists (S6)."""

from decimal import Decimal

import pytest

from app.domain.targets import GOAL_FACTORS, calculate_target_estimate
from tests.test_acceptance_gaps import make_user, session_factory  # noqa: F401


def test_ac_119_build_muscle_estimate_worked_example():
    # Male, 80 kg, 180 cm, age 25, moderate (as AC-19): TDEE 2,797.75
    # x 1.10 = 3,077.525 -> nearest 10 = 3,080 kcal; protein 1.6 x 80 = 128 g;
    # fat 25% of 3,080 = 770 kcal / 9 = 85.6 -> 86 g; carbs (3,080 - 512 - 770) / 4 = 449.5 -> 450 g
    est = calculate_target_estimate(
        weight_kg=Decimal("80"),
        height_cm=Decimal("180"),
        age=25,
        sex="male",
        activity_level="moderate",
        goal="build_muscle",
    )
    assert est.calories == 3080
    assert est.protein_g == 128
    assert est.fat_g == 86
    assert est.carbs_g == 450
    assert est.assumptions["goal"] == "build_muscle"
    assert est.assumptions["goal_factor"] == Decimal("1.10")


def test_no_goal_reduces_calories():
    # Spec S6 / D-11: there is still no deficit or weight-loss goal
    assert set(GOAL_FACTORS) == {"maintain", "build_strength", "build_muscle"}
    assert all(factor >= Decimal("1.0") for factor in GOAL_FACTORS.values())


@pytest.mark.asyncio
async def test_ac_119_profile_and_estimate_api_accept_build_muscle(session_factory):  # noqa: F811
    _, client = await make_user(session_factory, "muscle@example.com")
    async with client:
        prof = await client.patch("/api/profile", json={"goal": "build_muscle"})
        assert prof.status_code == 200, prof.text
        assert prof.json()["goal"] == "build_muscle"

        est = await client.post(
            "/api/nutrition/goals/estimate",
            json={
                "weight_kg": "80",
                "height_cm": "180",
                "age": 25,
                "sex_for_estimate": "male",
                "activity_level": "moderate",
                "goal": "build_muscle",
            },
        )
        assert est.status_code == 200, est.text
        body = est.json()
        assert body["calories"] == 3080
        assert (body["protein_g"], body["fat_g"], body["carbs_g"]) == (128, 86, 450)
