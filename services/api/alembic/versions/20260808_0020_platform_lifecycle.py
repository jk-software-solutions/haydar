"""Add plan concurrency and coupon activation restrictions.

Revision ID: 20260808_0020
Revises: 20260808_0019
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0020"
down_revision: str | None = "20260808_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscription_plans",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("coupons", sa.Column("plan_id", sa.Uuid()))
    op.add_column("coupons", sa.Column("billing_cycle", sa.String(16)))
    op.create_foreign_key(
        "fk_coupons_plan",
        "coupons",
        "subscription_plans",
        ["plan_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_coupons_billing_cycle",
        "coupons",
        "billing_cycle IS NULL OR billing_cycle IN ('monthly', 'annual')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_coupons_billing_cycle", "coupons", type_="check")
    op.drop_constraint("fk_coupons_plan", "coupons", type_="foreignkey")
    op.drop_column("coupons", "billing_cycle")
    op.drop_column("coupons", "plan_id")
    op.drop_column("subscription_plans", "version")
