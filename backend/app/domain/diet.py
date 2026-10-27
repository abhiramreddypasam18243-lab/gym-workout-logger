"""Diet tag rules for the planner's hard filters (spec §5.5 step 1.2, AC-59, D-35).

Pure functions only — no framework, database, or clock imports (D-20, AC-98).
"""

from collections.abc import Iterable

# A recipe carrying the key tag also meets every tag in its value set.
# Eggs are not vegetarian in this catalogue (D-35), so vegetarian implies pescatarian
# only through plant and dairy foods.
DIET_TAG_IMPLIES: dict[str, frozenset[str]] = {
    "vegan": frozenset({"vegetarian", "pescatarian", "dairy_free"}),
    "vegetarian": frozenset({"pescatarian"}),
}

MEAL_SLOTS: tuple[str, ...] = ("breakfast", "lunch", "dinner", "snack")


def expand_diet_tags(tags: Iterable[str]) -> set[str]:
    """Return the recipe's own tags plus every tag they imply (vegan -> vegetarian ...)."""
    expanded = {t.strip().lower() for t in tags}
    for tag in list(expanded):
        expanded |= DIET_TAG_IMPLIES.get(tag, frozenset())
    return expanded


def contains_excluded(search_tokens: Iterable[str], excluded: str) -> bool:
    """Case-insensitive match of an excluded ingredient against ingredient and food names."""
    needle = excluded.strip().lower()
    return bool(needle) and any(needle in token for token in search_tokens)
