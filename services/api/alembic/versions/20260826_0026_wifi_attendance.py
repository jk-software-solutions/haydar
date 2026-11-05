"""Enable Wi-Fi attendance for existing subscription plans.

Revision ID: 20260826_0026
Revises: 20260808_0025
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260826_0026"
down_revision: str | None = "20260808_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE subscription_plans
            SET features = jsonb_set(COALESCE(features, '{}'::json)::jsonb, '{wifi}', 'true'::jsonb)::json
            WHERE is_active = true
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE subscription_plans
            SET features = (COALESCE(features, '{}'::json)::jsonb - 'wifi')::json
            WHERE is_active = true
            """
        )
    )
