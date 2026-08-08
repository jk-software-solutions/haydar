"""tenant protected file storage

Revision ID: 20260808_0011
Revises: 20260808_0010
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0011"
down_revision: str | None = "20260808_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stored_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "uploaded_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_stored_files_company_uploader",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stored_files_company_created", "stored_files", ["company_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_stored_files_company_created", table_name="stored_files")
    op.drop_table("stored_files")
