"""Tests for strength analytics domain functions: e1RM, volume, and PR detection.

Acceptance criteria:
AC-39 (5.2): e1RM (Epley): 80 kg × 5 gives 93.33 (displayed 93.3, labelled estimated);
            100 kg × 1 gives 100.0; 60 kg × 12 gives 84.0;
            13 reps returns null with rep_range; warm-up sets are excluded.
AC-40 (5.2): Volume for working sets 80 × 5, 80 × 5, 80 × 4 is 1,120 kg;
            a 40 × 10 warm-up is excluded.
AC-41 (5.2): For sets 80 × 5, 85 × 5, 90 × 3 in order:
            the first is baseline, 85 × 5 (e1RM 99.17) is a PR, and 90 × 3 (e1RM 99.0) is not;
            an equal e1RM is not a PR; deleting the PR set recomputes PRs.
AC-43 (NFR): e1RM uses exact decimals: 82.5 kg × 3 reps gives exactly 90.75.
"""

from datetime import UTC, datetime
from decimal import Decimal

from app.domain.strength import (
    StrengthSetInput,
    calculate_epley_e1rm,
    calculate_working_volume,
    detect_personal_records,
)


def test_ac_39_e1rm_epley_cases():
    # 80 kg × 5 reps = 80 * (1 + 5/30) = 80 * (7/6) = 93.3333...
    res_80_5 = calculate_epley_e1rm(load_kg=Decimal("80"), reps=5, is_warmup=False)
    assert res_80_5.e1rm is not None
    # 2 decimal places check: 93.33; 1 decimal place display: 93.3
    assert round(res_80_5.e1rm, 2) == Decimal("93.33")
    assert res_80_5.display_e1rm == "93.3"
    assert res_80_5.reason is None

    # 100 kg × 1 rep = 100.0 (identity for 1 rep)
    res_100_1 = calculate_epley_e1rm(load_kg=Decimal("100"), reps=1, is_warmup=False)
    assert res_100_1.e1rm == Decimal("100.0")
    assert res_100_1.display_e1rm == "100.0"

    # 60 kg × 12 reps = 60 * (1 + 12/30) = 60 * 1.4 = 84.0
    res_60_12 = calculate_epley_e1rm(load_kg=Decimal("60"), reps=12, is_warmup=False)
    assert res_60_12.e1rm == Decimal("84.0")
    assert res_60_12.display_e1rm == "84.0"

    # 13 reps: returns null with reason 'rep_range'
    res_13 = calculate_epley_e1rm(load_kg=Decimal("60"), reps=13, is_warmup=False)
    assert res_13.e1rm is None
    assert res_13.reason == "rep_range"

    # Warm-up set: excluded (returns null with reason 'warmup')
    res_warmup = calculate_epley_e1rm(load_kg=Decimal("80"), reps=5, is_warmup=True)
    assert res_warmup.e1rm is None
    assert res_warmup.reason == "warmup"


def test_ac_40_working_volume():
    # Working sets: 80 × 5, 80 × 5, 80 × 4 -> (400 + 400 + 320) = 1,120 kg
    # Warm-up set: 40 × 10 -> excluded
    sets = [
        StrengthSetInput(load_kg=Decimal("40"), reps=10, is_warmup=True),
        StrengthSetInput(load_kg=Decimal("80"), reps=5, is_warmup=False),
        StrengthSetInput(load_kg=Decimal("80"), reps=5, is_warmup=False),
        StrengthSetInput(load_kg=Decimal("80"), reps=4, is_warmup=False),
    ]
    volume = calculate_working_volume(sets)
    assert volume == Decimal("1120")


def test_ac_41_pr_detection():
    # Sets in order:
    # 1. 80 × 5 (e1RM ~93.33) -> baseline, NOT flagged as PR
    # 2. 85 × 5 (e1RM 85 * 7/6 = 99.166... = 99.17) -> strictly greater -> IS PR
    # 3. 90 × 3 (e1RM 90 * 1.1 = 99.0) -> not strictly greater than 99.17 -> NOT PR
    t0 = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 15, 10, 5, tzinfo=UTC)
    t2 = datetime(2026, 10, 15, 10, 10, tzinfo=UTC)

    sets = [
        StrengthSetInput(
            load_kg=Decimal("80"), reps=5, is_warmup=False, set_number=1, completed_at=t0
        ),
        StrengthSetInput(
            load_kg=Decimal("85"), reps=5, is_warmup=False, set_number=2, completed_at=t1
        ),
        StrengthSetInput(
            load_kg=Decimal("90"), reps=3, is_warmup=False, set_number=3, completed_at=t2
        ),
    ]

    results = detect_personal_records(sets)
    assert len(results) == 3

    # Set 1: baseline
    assert results[0].is_baseline is True
    assert results[0].is_pr is False

    # Set 2: PR
    assert results[1].is_baseline is False
    assert results[1].is_pr is True
    assert round(results[1].e1rm, 2) == Decimal("99.17")

    # Set 3: Not PR (99.0 <= 99.17)
    assert results[2].is_baseline is False
    assert results[2].is_pr is False
    assert results[2].e1rm == Decimal("99.0")


def test_ac_41_equal_e1rm_not_pr():
    # Equal e1RM is NOT a PR
    t0 = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 15, 10, 5, tzinfo=UTC)
    t2 = datetime(2026, 10, 15, 10, 10, tzinfo=UTC)

    sets = [
        # e1RM 84.0 (baseline)
        StrengthSetInput(
            load_kg=Decimal("60"), reps=12, is_warmup=False, set_number=1, completed_at=t0
        ),
        # e1RM 70 * 1.2 = 84.0 (equal -> not PR)
        StrengthSetInput(
            load_kg=Decimal("70"), reps=6, is_warmup=False, set_number=2, completed_at=t1
        ),
        # e1RM 84.0 (equal -> not PR)
        StrengthSetInput(
            load_kg=Decimal("84"), reps=1, is_warmup=False, set_number=3, completed_at=t2
        ),
    ]
    results = detect_personal_records(sets)
    assert results[0].is_baseline is True
    assert results[0].is_pr is False
    assert results[1].is_pr is False
    assert results[2].is_pr is False


def test_ac_41_deleting_pr_set_recomputes():
    # If the middle PR set (85 × 5) is removed, remaining sets recompute
    t0 = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 15, 10, 10, tzinfo=UTC)

    # Only set 1 and set 3
    remaining_sets = [
        # e1RM ~93.33 (baseline)
        StrengthSetInput(
            load_kg=Decimal("80"), reps=5, is_warmup=False, set_number=1, completed_at=t0
        ),
        # e1RM 99.0 (> 93.33 -> now it becomes PR!)
        StrengthSetInput(
            load_kg=Decimal("90"), reps=3, is_warmup=False, set_number=2, completed_at=t2
        ),
    ]
    results = detect_personal_records(remaining_sets)
    assert results[0].is_baseline is True
    assert results[0].is_pr is False
    assert results[1].is_baseline is False
    assert results[1].is_pr is True


def test_ac_43_exact_decimal_e1rm():
    # 82.5 kg × 3 reps gives exactly 90.75
    # 82.5 * (1 + 3/30) = 82.5 * 1.1 = 90.75 exactly
    res = calculate_epley_e1rm(load_kg=Decimal("82.5"), reps=3, is_warmup=False)
    assert res.e1rm == Decimal("90.75")
