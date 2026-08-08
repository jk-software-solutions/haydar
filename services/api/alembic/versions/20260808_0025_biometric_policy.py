"""Add the company attendance biometric policy.

Revision ID: 20260808_0025
Revises: 20260808_0024
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0025"
down_revision: str | None = "20260808_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "attendance_biometric_policy",
            sa.String(16),
            server_default="optional",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_companies_attendance_biometric_policy",
        "companies",
        "attendance_biometric_policy IN ('disabled', 'optional', 'required')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_companies_attendance_biometric_policy", "companies", type_="check"
    )
    op.drop_column("companies", "attendance_biometric_policy")
