"""Progressive overload hint and weekly set counting (D-33, D-34, AC-123, AC-125).

Pure functions only — no framework, database, or clock imports (D-20, AC-98).

The hint is a simple double-progression rule, not coaching advice: work at the same
load until every working set at that load reaches the top of the rep range, then add
one step. It never suggests a lower load.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.domain.strength import StrengthSetInput


@dataclass(frozen=True)
class OverloadHint:
    action: Literal["increase_load", "keep_load"]
    top_load_kg: Decimal
    suggested_load_kg: Decimal
    reps_at_top_load: tuple[int, ...]
    rep_min: int
    rep_max: int
    reason: str


def suggest_next_load(
    sets: Sequence[StrengthSetInput],
    rep_min: int,
    rep_max: int,
    step_kg: Decimal,
) -> OverloadHint | None:
    """Hint for the next session from the last session's sets of one exercise.

    Only working sets at the heaviest load count. Returns None with no working sets.
    """
    if rep_min < 1 or rep_max < rep_min:
        raise ValueError("rep range must satisfy 1 <= rep_min <= rep_max")
    working = [s for s in sets if not s.is_warmup and s.reps > 0]
    if not working:
        return None

    top = max(s.load_kg for s in working)
    reps = tuple(s.reps for s in sorted(working, key=lambda s: s.set_number) if s.load_kg == top)

    if all(r >= rep_max for r in reps):
        return OverloadHint(
            action="increase_load",
            top_load_kg=top,
            suggested_load_kg=top + step_kg,
            reps_at_top_load=reps,
            rep_min=rep_min,
            rep_max=rep_max,
            reason=f"Every set at the top load reached {rep_max} reps, the top of your {rep_min}–{rep_max} range.",
        )
    if any(r < rep_min for r in reps):
        reason = f"Some sets fell below {rep_min} reps; stay at this load until every set reaches {rep_min}."
    else:
        reason = f"Keep this load and add reps until every set reaches {rep_max}."
    return OverloadHint(
        action="keep_load",
        top_load_kg=top,
        suggested_load_kg=top,
        reps_at_top_load=reps,
        rep_min=rep_min,
        rep_max=rep_max,
        reason=reason,
    )


def count_working_sets_by_muscle(sets: Iterable[tuple[str, bool]]) -> dict[str, int]:
    """Count working sets per muscle from (primary_muscle, is_warmup) pairs (D-34)."""
    counts: Counter[str] = Counter()
    for muscle, is_warmup in sets:
        if not is_warmup:
            counts[muscle.strip().lower()] += 1
    return dict(counts)
