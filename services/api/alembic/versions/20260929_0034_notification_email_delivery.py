"""Track notification emails that were delivered."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0034"
down_revision: str | None = "20260926_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notifications", "email_sent_at")
