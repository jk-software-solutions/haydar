"""Add employee profile photos.

Revision ID: 20260914_0029
Revises: 20260908_0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260914_0029"
down_revision: str | None = "20260908_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "employee_profiles",
        sa.Column("avatar_file_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_employee_profiles_company_avatar",
        "employee_profiles",
        "stored_files",
        ["company_id", "avatar_file_id"],
        ["company_id", "id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_employee_profiles_company_avatar",
        "employee_profiles",
        type_="foreignkey",
    )
    op.drop_column("employee_profiles", "avatar_file_id")
