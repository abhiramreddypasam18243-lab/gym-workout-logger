"""The 14 EU allergen codes (spec §6, S9, D-31).

Catalogue foods and user allergy constraints must use the same codes, because the
planner's allergy filter is an exact match. Older clients sent `cereals_gluten` and
`soybeans`; those spellings are accepted and mapped to the catalogue codes.
"""

EU_ALLERGENS: tuple[str, ...] = (
    "gluten",
    "crustaceans",
    "eggs",
    "fish",
    "peanuts",
    "soy",
    "milk",
    "tree_nuts",
    "celery",
    "mustard",
    "sesame",
    "sulphites",
    "lupin",
    "molluscs",
)

ALLERGEN_ALIASES: dict[str, str] = {
    "cereals_gluten": "gluten",
    "cereals_containing_gluten": "gluten",
    "soybeans": "soy",
    "soya": "soy",
    "egg": "eggs",
}


def normalize_allergen(value: str) -> str | None:
    """Return the catalogue code for an allergen, or None if it is not one of the 14."""
    code = value.strip().lower().replace(" ", "_").replace("-", "_")
    code = ALLERGEN_ALIASES.get(code, code)
    return code if code in EU_ALLERGENS else None
