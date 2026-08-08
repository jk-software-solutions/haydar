"""Add persistent mutation idempotency records.

Revision ID: 20260808_0018
Revises: 20260808_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0018"
down_revision: str | None = "20260808_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(120), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("response_body", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_idempotency_records_company_member",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_idempotency_records_operation_key",
        "idempotency_records",
        ["company_id", "membership_id", "operation", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_idempotency_records_expires",
        "idempotency_records",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_expires", table_name="idempotency_records")
    op.drop_index(
        "uq_idempotency_records_operation_key", table_name="idempotency_records"
    )
    op.drop_table("idempotency_records")
