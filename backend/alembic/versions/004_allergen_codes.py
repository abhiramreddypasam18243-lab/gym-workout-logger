"""Map legacy allergy spellings to catalogue allergen codes (D-31, AC-121)

The settings screen saved `cereals_gluten` and `soybeans`, but catalogue foods are
tagged `gluten` and `soy`, so those allergies never matched in the planner's filter.

Revision ID: 004_allergen_codes
Revises: 003_build_muscle_goal
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004_allergen_codes"
down_revision: str | None = "003_build_muscle_goal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY = {
    "cereals_gluten": "gluten",
    "cereals_containing_gluten": "gluten",
    "soybeans": "soy",
    "soya": "soy",
    "egg": "eggs",
}


def upgrade() -> None:
    for old, new in LEGACY.items():
        op.execute(
            sa.text(
                "UPDATE user_food_constraints SET constraint_value = :new "
                "WHERE constraint_type = 'allergy' AND lower(constraint_value) = :old"
            ).bindparams(new=new, old=old)
        )


def downgrade() -> None:
    # The new codes are what the catalogue uses; going back would re-break the filter
    pass
