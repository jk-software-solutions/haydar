"""Add attendance leaderboard anonymization policy.

Revision ID: 20260808_0024
Revises: 20260808_0023
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0024"
down_revision: str | None = "20260808_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "attendance_leaderboard_settings",
        sa.Column("anonymize", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("attendance_leaderboard_settings", "anonymize")
