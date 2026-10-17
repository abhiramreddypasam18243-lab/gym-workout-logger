"""Strength analytics domain functions: e1RM, volume, and PR detection.

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
All calculations use exact Decimals (D-05, AC-43).
Implements Epley formula (1–12 reps), working volume summation, and chronological
personal record detection (spec §5.2, AC-39–41, AC-43).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal


@dataclass(frozen=True)
class StrengthSetInput:
    """Input set data for strength analytics."""

    load_kg: Decimal
    reps: int
    is_warmup: bool = False
    set_number: int = 1
    completed_at: datetime | None = None


@dataclass(frozen=True)
class E1rmResult:
    """Estimated 1RM calculation result with transparency labelling."""

    e1rm: Decimal | None
    display_e1rm: str | None
    reason: Literal["warmup", "rep_range"] | None = None
    is_estimated: bool = True


@dataclass(frozen=True)
class SetPrResult:
    """Personal record evaluation result for a set."""

    set_input: StrengthSetInput
    e1rm: Decimal | None
    is_baseline: bool
    is_pr: bool


def calculate_epley_e1rm(
    load_kg: Decimal,
    reps: int,
    is_warmup: bool = False,
) -> E1rmResult:
    """Calculate Estimated 1RM using Epley's formula.

    Formula: e1RM = load × (1 + reps / 30)
    Rules (spec §5.2, AC-39, AC-43):
    - For reps = 1, e1RM = load exactly.
    - Valid only for working sets with 1 to 12 reps.
    - If reps > 12 or reps < 1, returns null with reason 'rep_range'.
    - Warm-up sets are excluded, returning null with reason 'warmup'.
    - Display rounding is half-up to 1 decimal place.
    """
    if is_warmup:
        return E1rmResult(e1rm=None, display_e1rm=None, reason="warmup")

    if reps < 1 or reps > 12:
        return E1rmResult(e1rm=None, display_e1rm=None, reason="rep_range")

    e1rm = load_kg if reps == 1 else load_kg * (Decimal("1") + Decimal(reps) / Decimal("30"))

    display = str(e1rm.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    return E1rmResult(e1rm=e1rm, display_e1rm=display, reason=None)


def calculate_working_volume(sets: Iterable[StrengthSetInput]) -> Decimal:
    """Sum volume (load × reps) across working sets only (spec §5.2, AC-40).

    Warm-up sets (is_warmup = True) are strictly excluded.
    """
    total_volume = Decimal("0")
    for s in sets:
        if not s.is_warmup:
            total_volume += s.load_kg * Decimal(s.reps)
    return total_volume


def detect_personal_records(sets: list[StrengthSetInput]) -> list[SetPrResult]:
    """Detect Personal Records (PRs) across chronologically ordered working sets.

    Rules (spec §5.2, AC-41):
    - Sets are ordered chronologically by completed_at (ascending), then set_number (ascending).
    - The first working set with a valid e1RM is the baseline (is_baseline = True, is_pr = False).
    - Subsequent working sets are PRs if and only if their e1RM is strictly greater
      than the highest e1RM of all prior working sets.
    - Equal e1RMs are NOT PRs.
    - Warm-up sets and sets outside rep range are not eligible for baseline or PR.
    """
    # Sort chronologically if timestamps are provided, falling back to set_number
    sorted_sets = sorted(
        sets,
        key=lambda s: (
            s.completed_at if s.completed_at is not None else datetime.min,
            s.set_number,
        ),
    )

    results: list[SetPrResult] = []
    best_e1rm: Decimal | None = None
    has_baseline = False

    for s in sorted_sets:
        e1rm_res = calculate_epley_e1rm(s.load_kg, s.reps, s.is_warmup)
        e1rm = e1rm_res.e1rm

        if e1rm is None:
            results.append(
                SetPrResult(
                    set_input=s,
                    e1rm=None,
                    is_baseline=False,
                    is_pr=False,
                )
            )
            continue

        if not has_baseline:
            # First working set is the baseline benchmark
            has_baseline = True
            best_e1rm = e1rm
            results.append(
                SetPrResult(
                    set_input=s,
                    e1rm=e1rm,
                    is_baseline=True,
                    is_pr=False,
                )
            )
        else:
            # Must be strictly greater than best so far
            assert best_e1rm is not None
            if e1rm > best_e1rm:
                best_e1rm = e1rm
                results.append(
                    SetPrResult(
                        set_input=s,
                        e1rm=e1rm,
                        is_baseline=False,
                        is_pr=True,
                    )
                )
            else:
                results.append(
                    SetPrResult(
                        set_input=s,
                        e1rm=e1rm,
                        is_baseline=False,
                        is_pr=False,
                    )
                )

    return results
