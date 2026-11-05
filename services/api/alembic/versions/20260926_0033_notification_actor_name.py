"""Store the actor name shown with in-app notifications.

Revision ID: 20260926_0033
Revises: 20260920_0032
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260926_0033"
down_revision: str | None = "20260920_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("actor_name", sa.String(length=160), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notifications", "actor_name")
