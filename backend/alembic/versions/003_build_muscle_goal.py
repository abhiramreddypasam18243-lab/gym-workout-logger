"""Allow the build_muscle goal (D-29, AC-119)

Revision ID: 003_build_muscle_goal
Revises: 002_align_indexes
Create Date: 2026-10-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "003_build_muscle_goal"
down_revision: str | None = "002_align_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW = "goal IN ('maintain', 'build_strength', 'build_muscle')"
OLD = "goal IN ('maintain', 'build_strength')"


def _replace_goal_check(sql: str) -> None:
    # batch mode recreates the table on SQLite, which cannot ALTER constraints
    with op.batch_alter_table("user_profiles", recreate="auto") as batch:
        batch.drop_constraint("chk_profile_goal", type_="check")
        batch.create_check_constraint("chk_profile_goal", sql)


def upgrade() -> None:
    _replace_goal_check(NEW)


def downgrade() -> None:
    op.execute("UPDATE user_profiles SET goal = 'build_strength' WHERE goal = 'build_muscle'")
    _replace_goal_check(OLD)
