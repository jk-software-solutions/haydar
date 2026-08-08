"""Add per-member QR replay protection.

Revision ID: 20260808_0015
Revises: 20260808_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0015"
down_revision: str | None = "20260808_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_branch_qr_tokens_company_id", "branch_qr_tokens", ["company_id", "id"]
    )
    op.create_table(
        "branch_qr_token_uses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_branch_qr_token_uses_company_id_companies"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_branch_qr_token_uses_company_member",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "token_id"],
            ["branch_qr_tokens.company_id", "branch_qr_tokens.id"],
            name="fk_branch_qr_token_uses_company_token",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_branch_qr_token_uses")),
        sa.UniqueConstraint(
            "token_id", "membership_id", "action", name="uq_branch_qr_token_uses_replay"
        ),
    )
    op.create_index(
        "ix_branch_qr_token_uses_company_used",
        "branch_qr_token_uses",
        ["company_id", "used_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_branch_qr_token_uses_company_used", table_name="branch_qr_token_uses")
    op.drop_table("branch_qr_token_uses")
    op.drop_constraint("uq_branch_qr_tokens_company_id", "branch_qr_tokens", type_="unique")
