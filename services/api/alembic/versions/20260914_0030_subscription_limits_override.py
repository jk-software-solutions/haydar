"""Allow per-company subscription limit overrides.

Revision ID: 20260914_0030
Revises: 20260914_0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260914_0030"
down_revision: str | None = "20260914_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "company_subscriptions",
        sa.Column("limits_override", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("company_subscriptions", "limits_override")
