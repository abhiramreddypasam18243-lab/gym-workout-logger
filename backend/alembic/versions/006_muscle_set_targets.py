"""Weekly working-set targets per muscle group (D-34, AC-125)

Revision ID: 006_muscle_set_targets
Revises: 005_custom_foods
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006_muscle_set_targets"
down_revision: str | None = "005_custom_foods"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "muscle_set_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("muscle", sa.String(50), nullable=False),
        sa.Column("weekly_sets", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "muscle", name="uq_muscle_set_target_user_muscle"),
        sa.CheckConstraint("weekly_sets BETWEEN 1 AND 40", name="chk_muscle_set_target_range"),
    )
    op.create_index("ix_muscle_set_targets_user_id", "muscle_set_targets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_muscle_set_targets_user_id", table_name="muscle_set_targets")
    op.drop_table("muscle_set_targets")
