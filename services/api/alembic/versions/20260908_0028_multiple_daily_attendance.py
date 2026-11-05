"""Allow multiple closed attendance sessions in one work day.

Revision ID: 20260908_0028
Revises: 20260908_0027
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260908_0028"
down_revision: str | None = "20260908_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_attendance_records_member_date", "attendance_records", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_attendance_records_member_date",
        "attendance_records",
        ["company_id", "membership_id", "work_date"],
    )
