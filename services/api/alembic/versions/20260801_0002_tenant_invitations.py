"""tenant scoped invitations

Revision ID: 20260801_0002
Revises: 20260801_0001
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0002"
down_revision: str | None = "20260801_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_company_memberships_company_id",
        "company_memberships",
        ["company_id", "id"],
    )
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("invited_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("role_code", sa.String(length=40), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_invitations_company_id_companies"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "invited_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_invitations_company_inviter",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invitations")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_invitations_token_hash")),
    )
    op.create_index(
        "ix_invitations_company_email",
        "invitations",
        ["company_id", "email"],
        unique=False,
    )
    op.create_index(
        "ix_invitations_company_status",
        "invitations",
        ["company_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_invitations_company_status", table_name="invitations")
    op.drop_index("ix_invitations_company_email", table_name="invitations")
    op.drop_table("invitations")
    op.drop_constraint(
        "uq_company_memberships_company_id",
        "company_memberships",
        type_="unique",
    )
