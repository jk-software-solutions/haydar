"""Increase the trial branch allowance for multi-branch evaluation.

Revision ID: 20260808_0012
Revises: 20260808_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0012"
down_revision: str | None = "20260808_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE subscription_plans
            SET limits = jsonb_set(limits::jsonb, '{branches}', '3'::jsonb)::json
            WHERE code = 'FREE_TRIAL'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE subscription_plans
            SET limits = jsonb_set(limits::jsonb, '{branches}', '1'::jsonb)::json
            WHERE code = 'FREE_TRIAL'
            """
        )
    )
