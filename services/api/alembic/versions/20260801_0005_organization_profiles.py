"""company settings and tenant employee profiles

Revision ID: 20260801_0005
Revises: 20260801_0004
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0005"
down_revision: str | None = "20260801_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("default_locale", sa.String(length=8), server_default="ar", nullable=False),
    )
    op.add_column(
        "companies",
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="Asia/Riyadh",
            nullable=False,
        ),
    )
    op.add_column(
        "companies",
        sa.Column("country_code", sa.String(length=2), server_default="SA", nullable=False),
    )

    op.create_table(
        "employee_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("employee_number", sa.String(length=64), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column(
            "employment_type",
            sa.String(length=32),
            server_default="full_time",
            nullable=False,
        ),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column(
            "preferred_locale",
            sa.String(length=8),
            server_default="ar",
            nullable=False,
        ),
        sa.Column(
            "attendance_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_employee_profiles_company_id_companies"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_profiles_company_membership",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_profiles")),
        sa.UniqueConstraint(
            "company_id",
            "employee_number",
            name="uq_employee_profiles_company_employee_number",
        ),
        sa.UniqueConstraint(
            "company_id",
            "membership_id",
            name="uq_employee_profiles_company_membership",
        ),
    )
    op.create_index(
        "ix_employee_profiles_company_active",
        "employee_profiles",
        ["company_id", "attendance_enabled"],
        unique=False,
    )
    op.execute(
        sa.text(
            """
            INSERT INTO employee_profiles (
                id, company_id, membership_id, display_name, employment_type,
                preferred_locale, attendance_enabled, version, created_at, updated_at
            )
            SELECT
                gen_random_uuid(), membership.company_id, membership.id, users.full_name,
                'full_time', 'ar', true, 1, now(), now()
            FROM company_memberships AS membership
            JOIN users ON users.id = membership.user_id
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_employee_profiles_company_active", table_name="employee_profiles")
    op.drop_table("employee_profiles")
    op.drop_column("companies", "country_code")
    op.drop_column("companies", "timezone")
    op.drop_column("companies", "default_locale")
