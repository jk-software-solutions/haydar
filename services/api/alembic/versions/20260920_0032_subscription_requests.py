"""Add customer subscription purchase requests.

Revision ID: 20260920_0032
Revises: 20260917_0031
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260920_0032"
down_revision: str | None = "20260917_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscription_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_membership_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("billing_cycle", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("coupon_code", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_subscription_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["requested_by_membership_id"], ["company_memberships.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["activated_subscription_id"], ["company_subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subscription_requests_company_status",
        "subscription_requests",
        ["company_id", "status"],
    )
    op.create_index(
        "ix_subscription_requests_created",
        "subscription_requests",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_subscription_requests_created", table_name="subscription_requests")
    op.drop_index("ix_subscription_requests_company_status", table_name="subscription_requests")
    op.drop_table("subscription_requests")
