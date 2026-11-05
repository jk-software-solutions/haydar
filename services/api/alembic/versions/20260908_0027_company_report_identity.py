"""Store company identity fields for client-facing reports.

Revision ID: 20260908_0027
Revises: 20260826_0026
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "20260908_0027"
down_revision: str | None = "20260826_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("commercial_registration_number", sa.String(32), nullable=True))
    op.add_column("companies", sa.Column("unified_number", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "unified_number")
    op.drop_column("companies", "commercial_registration_number")
