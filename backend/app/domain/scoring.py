"""Meal plan candidate scoring and serving size selection domain functions.

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
Implements candidate fit calculation, serving size selection, and multi-factor
candidate ranking (spec §5.5, AC-63, AC-64).
"""

from collections.abc import Mapping
from decimal import Decimal

# Allowed serving sizes for plan generation (spec §5.5, AC-64)
ALLOWED_SERVING_SIZES: tuple[Decimal, ...] = (
    Decimal("0.5"),
    Decimal("1.0"),
    Decimal("1.5"),
    Decimal("2.0"),
    Decimal("2.5"),
    Decimal("3.0"),
)

# Initial scoring weights (spec §5.5)
DEFAULT_WEIGHTS: dict[str, Decimal] = {
    "w_t": Decimal("1.0"),  # Target fit
    "w_c": Decimal("0.3"),  # Cuisine match
    "w_p": Decimal("0.2"),  # Preparation time penalty
    "w_b": Decimal("0.2"),  # Budget ratio penalty
    "w_r": Decimal("0.5"),  # Repetition penalty
}


def calculate_target_fit(
    cand_kcal: Decimal | None,
    cand_protein: Decimal | None,
    slot_kcal: Decimal | None,
    slot_protein: Decimal | None,
) -> Decimal:
    """Calculate target fit score using relative errors.

    target_fit = - ( |kcal - slot_kcal| / slot_kcal + |protein - slot_protein| / slot_protein ) / 2
    Uses only targets that exist (spec §5.5, AC-63).
    """
    terms: list[Decimal] = []

    if slot_kcal is not None and slot_kcal > Decimal("0") and cand_kcal is not None:
        terms.append(abs(cand_kcal - slot_kcal) / slot_kcal)

    if slot_protein is not None and slot_protein > Decimal("0") and cand_protein is not None:
        terms.append(abs(cand_protein - slot_protein) / slot_protein)

    if not terms:
        return Decimal("0")

    avg_deviation = sum(terms) / Decimal(len(terms))
    return -avg_deviation


def calculate_candidate_score(
    target_fit: Decimal,
    cuisine_match: Decimal,
    total_minutes: int,
    budget_ratio: Decimal = Decimal("0"),
    repetition: int = 0,
    weights: Mapping[str, Decimal] | None = None,
) -> Decimal:
    """Calculate candidate score across target fit, cuisine match, prep time, budget,
    and repetition.

    score = w_t × target_fit + w_c × cuisine_match
            − w_p × (total minutes / 60)
            − w_b × budget_ratio
            − w_r × repetition
    (spec §5.5, AC-63)
    """
    w = DEFAULT_WEIGHTS if weights is None else weights

    time_fraction = Decimal(total_minutes) / Decimal("60")

    return (
        w["w_t"] * target_fit
        + w["w_c"] * cuisine_match
        - w["w_p"] * time_fraction
        - w["w_b"] * budget_ratio
        - w["w_r"] * Decimal(repetition)
    )


def select_best_serving_size(
    recipe_kcal_per_serving: Decimal,
    slot_kcal: Decimal,
    allowed_sizes: tuple[Decimal, ...] = ALLOWED_SERVING_SIZES,
) -> Decimal:
    """Choose the serving size that minimises |kcal - slot_kcal|.

    Ties go to the smaller size (spec §5.5, AC-64).
    """
    best_size = allowed_sizes[0]
    min_deviation = abs((recipe_kcal_per_serving * best_size) - slot_kcal)

    for s in allowed_sizes[1:]:
        cand_kcal = recipe_kcal_per_serving * s
        dev = abs(cand_kcal - slot_kcal)
        # Strictly smaller deviation beats previous, preserving smaller size on tie
        if dev < min_deviation:
            min_deviation = dev
            best_size = s

    return best_size


def affordable_serving_sizes(
    cost_minor_per_serving: int | None,
    slot_budget_minor: Decimal | None,
    allowed_sizes: tuple[Decimal, ...] = ALLOWED_SERVING_SIZES,
) -> tuple[Decimal, ...]:
    """Serving sizes whose cost fits the slot's share of the daily budget (D-30, AC-120).

    With no budget, or a recipe without a cost, every allowed size is returned.
    Example: Rs 40 per serving and a Rs 37.50 slot budget allow only 0.5 (Rs 20).
    """
    if slot_budget_minor is None or cost_minor_per_serving is None:
        return allowed_sizes
    cost = Decimal(cost_minor_per_serving)
    return tuple(s for s in allowed_sizes if cost * s <= slot_budget_minor)
