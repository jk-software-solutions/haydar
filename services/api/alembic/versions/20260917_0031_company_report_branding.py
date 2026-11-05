"""Add optional company contact, tax, and report logo metadata.

Revision ID: 20260917_0031
Revises: 20260914_0030
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260917_0031"
down_revision: str | None = "20260914_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("contact_phone", sa.String(32), nullable=True))
    op.add_column("companies", sa.Column("tax_number", sa.String(32), nullable=True))
    op.add_column("companies", sa.Column("logo_file_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_companies_logo_file",
        "companies",
        "stored_files",
        ["id", "logo_file_id"],
        ["company_id", "id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_companies_logo_file", "companies", type_="foreignkey")
    op.drop_column("companies", "logo_file_id")
    op.drop_column("companies", "tax_number")
    op.drop_column("companies", "contact_phone")
