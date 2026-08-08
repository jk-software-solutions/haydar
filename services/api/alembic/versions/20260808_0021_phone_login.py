"""Add unique verified phone login identities.

Revision ID: 20260808_0021
Revises: 20260808_0020
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0021"
down_revision: str | None = "20260808_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_e164", sa.String(16)))
    op.add_column("users", sa.Column("phone_verified_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint("uq_users_phone_e164", "users", ["phone_e164"])


def downgrade() -> None:
    op.drop_constraint("uq_users_phone_e164", "users", type_="unique")
    op.drop_column("users", "phone_verified_at")
    op.drop_column("users", "phone_e164")
