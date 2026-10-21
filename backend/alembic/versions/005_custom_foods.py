"""User-owned custom foods (D-32, AC-122)

Revision ID: 005_custom_foods
Revises: 004_allergen_codes
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005_custom_foods"
down_revision: str | None = "004_allergen_codes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL owner = reviewed catalogue food; set = a food one user entered for themselves
    with op.batch_alter_table("foods", recreate="auto") as batch:
        batch.add_column(
            sa.Column(
                "owner_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", name="fk_foods_owner_user_id", ondelete="CASCADE"),
                nullable=True,
            )
        )
        batch.create_index("ix_foods_owner_user_id", ["owner_user_id"])


def downgrade() -> None:
    op.execute("DELETE FROM foods WHERE owner_user_id IS NOT NULL")
    with op.batch_alter_table("foods", recreate="auto") as batch:
        batch.drop_index("ix_foods_owner_user_id")
        batch.drop_column("owner_user_id")
