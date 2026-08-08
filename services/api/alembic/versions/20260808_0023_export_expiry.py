"""Add expiry and cleanup indexing for report exports.

Revision ID: 20260808_0023
Revises: 20260808_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0023"
down_revision: str | None = "20260808_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("export_jobs", sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.execute(
        """
        UPDATE export_jobs
        SET expires_at = COALESCE(completed_at, created_at) + INTERVAL '7 days'
        """
    )
    op.alter_column("export_jobs", "expires_at", nullable=False)
    op.create_index(
        "ix_export_jobs_company_expires",
        "export_jobs",
        ["company_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_export_jobs_company_expires", table_name="export_jobs")
    op.drop_column("export_jobs", "expires_at")
