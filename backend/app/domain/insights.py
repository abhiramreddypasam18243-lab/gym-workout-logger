"""Descriptive, non-causal insight domain generator (spec §5.9, S8, AC-86, AC-87).

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
Enforces strict observational wording without causal claims.
Checked against banned causal vocabulary:
('caused', 'because', 'due to', 'led to', 'results in', 'proves', 'improves', 'enhances', 'maximizes', 'optimizes', 'boosts', 'cheat', 'bad', 'failed', 'guilt').
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

BANNED_WORDS: set[str] = {
    "caused",
    "because",
    "due to",
    "led to",
    "results in",
    "proves",
    "improves",
    "enhances",
    "maximizes",
    "optimizes",
    "boosts",
    "cheat",
    "bad",
    "failed",
    "guilt",
    "streak lost",
}

DEFAULT_LIMITATIONS_STATEMENT = (
    "Observational correlation across logged records only. Unmeasured variables including sleep quality, "
    "hydration, stress, and program periodization were not controlled."
)


@dataclass(frozen=True)
class GeneratedInsight:
    """Non-causal descriptive insight with mandatory provenance metadata (AC-86, AC-87)."""

    id: str
    title: str
    window: str
    n: int
    statement: str
    limitations: str
    evidence: dict[str, Any]


def verify_non_causal_wording(text: str) -> None:
    """Validate that text contains zero causal or judgmental words (Rule S8, AC-87)."""
    text_lower = text.lower()
    for word in BANNED_WORDS:
        if word in text_lower:
            raise ValueError(f"Causal or judgmental word '{word}' detected in insight statement: {text}")


def generate_strength_trend_insight(
    exercise_name: str,
    window: str,
    e1rm_values: list[Decimal],
    session_dates: list[str],
) -> GeneratedInsight | None:
    """Generate a descriptive e1RM trend insight for an exercise across a time window (AC-86, AC-87).

    Rule AC-86: With fewer than 3 sessions of an exercise in the window,
    no trend insight is produced (returns None).
    """
    n = len(e1rm_values)
    if n < 3:
        return None

    first_e1rm = e1rm_values[0]
    last_e1rm = e1rm_values[-1]
    diff = last_e1rm - first_e1rm

    if diff > Decimal("0"):
        statement = (
            f"Over the {window.replace('_', ' ')} across {n} logged sessions of {exercise_name}, estimated 1RM differed by "
            f"+{diff:.1f} kg between the first session ({first_e1rm:.1f} kg) and the latest session ({last_e1rm:.1f} kg)."
        )
    elif diff < Decimal("0"):
        statement = (
            f"Over the {window.replace('_', ' ')} across {n} logged sessions of {exercise_name}, estimated 1RM differed by "
            f"{diff:.1f} kg between the first session ({first_e1rm:.1f} kg) and the latest session ({last_e1rm:.1f} kg)."
        )
    else:
        statement = (
            f"Over the {window.replace('_', ' ')} across {n} logged sessions of {exercise_name}, estimated 1RM remained steady "
            f"at {first_e1rm:.1f} kg across the observed period."
        )

    verify_non_causal_wording(statement)

    return GeneratedInsight(
        id=f"strength_trend_{exercise_name.lower().replace(' ', '_')}_{window}",
        title=f"{exercise_name} Observed Trend",
        window=window,
        n=n,
        statement=statement,
        limitations=DEFAULT_LIMITATIONS_STATEMENT,
        evidence={
            "initial_e1rm_kg": str(first_e1rm),
            "final_e1rm_kg": str(last_e1rm),
            "difference_kg": str(diff),
            "sessions_count": n,
            "first_date": session_dates[0] if session_dates else None,
            "last_date": session_dates[-1] if session_dates else None,
        },
    )


def generate_volume_nutrition_association_insight(
    window: str,
    days_protein_met: int,
    avg_vol_protein_met: Decimal,
    days_protein_not_met: int,
    avg_vol_protein_not_met: Decimal,
) -> GeneratedInsight | None:
    """Generate a non-causal association insight between protein adherence and training volume (AC-86, AC-87)."""
    total_days = days_protein_met + days_protein_not_met
    if total_days < 3:
        return None

    vol_diff = avg_vol_protein_met - avg_vol_protein_not_met

    statement = (
        f"During the {window.replace('_', ' ')}, days with logged protein intake at or above target coincided with an average session volume "
        f"of {avg_vol_protein_met:.0f} kg across {days_protein_met} sessions, compared to an average of "
        f"{avg_vol_protein_not_met:.0f} kg across {days_protein_not_met} sessions on other logged days."
    )

    verify_non_causal_wording(statement)

    return GeneratedInsight(
        id=f"protein_volume_association_{window}",
        title="Training Volume and Logged Protein Intake",
        window=window,
        n=total_days,
        statement=statement,
        limitations=DEFAULT_LIMITATIONS_STATEMENT,
        evidence={
            "days_protein_met": days_protein_met,
            "avg_volume_protein_met_kg": str(avg_vol_protein_met),
            "days_protein_not_met": days_protein_not_met,
            "avg_volume_protein_not_met_kg": str(avg_vol_protein_not_met),
            "volume_difference_kg": str(vol_diff),
        },
    )
