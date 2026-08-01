"""shifts overnight rules and assignments

Revision ID: 20260801_0007
Revises: 20260801_0006
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0007"
down_revision: str | None = "20260801_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    permissions = sa.table(
        "permissions", sa.column("code", sa.String), sa.column("description", sa.String)
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    op.bulk_insert(
        permissions,
        [
            {"code": "shifts:view", "description": "View company shifts and assignments"},
            {"code": "shifts:manage", "description": "Create and assign company shifts"},
        ],
    )
    op.bulk_insert(
        role_permissions,
        [
            {"role_code": role, "permission_code": permission}
            for role, permissions_for_role in {
                "OWNER": ("shifts:view", "shifts:manage"),
                "MANAGER": ("shifts:view", "shifts:manage"),
                "HR_OFFICER": ("shifts:view", "shifts:manage"),
                "SUPERVISOR": ("shifts:view",),
                "EMPLOYEE": ("shifts:view",),
            }.items()
            for permission in permissions_for_role
        ],
    )

    op.create_table(
        "shifts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_overnight", sa.Boolean(), nullable=False),
        sa.Column("working_days", sa.JSON(), nullable=False),
        sa.Column("grace_period_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("break_duration_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("recurrence", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("grace_period_minutes BETWEEN 0 AND 240", name="ck_shifts_grace_range"),
        sa.CheckConstraint(
            "break_duration_minutes BETWEEN 0 AND 720", name="ck_shifts_break_range"
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_shifts_effective_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_shifts_company_id_companies")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shifts")),
        sa.UniqueConstraint("company_id", "code", name="uq_shifts_company_code"),
        sa.UniqueConstraint("company_id", "id", name="uq_shifts_company_id"),
    )
    op.create_index("ix_shifts_company_active", "shifts", ["company_id", "is_active"])

    op.create_table(
        "shift_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=True),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(membership_id IS NULL) <> (branch_id IS NULL)", name="ck_shift_assignments_one_target"
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_shift_assignments_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_shift_assignments_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "shift_id"],
            ["shifts.company_id", "shifts.id"],
            name="fk_shift_assignments_company_shift",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_shift_assignments_company_membership",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_shift_assignments_company_branch",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "assigned_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_shift_assignments_company_actor",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shift_assignments")),
    )
    op.create_index(
        "ix_shift_assignments_employee_dates",
        "shift_assignments",
        ["company_id", "membership_id", "effective_from", "effective_to"],
    )
    op.create_index(
        "ix_shift_assignments_branch_dates",
        "shift_assignments",
        ["company_id", "branch_id", "effective_from", "effective_to"],
    )

    op.create_table(
        "shift_exceptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("exception_date", sa.Date(), nullable=False),
        sa.Column("is_working_day", sa.Boolean(), nullable=False),
        sa.Column("override_start_time", sa.Time(), nullable=True),
        sa.Column("override_end_time", sa.Time(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_shift_exceptions_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "shift_id"],
            ["shifts.company_id", "shifts.id"],
            name="fk_shift_exceptions_company_shift",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shift_exceptions")),
        sa.UniqueConstraint(
            "company_id",
            "shift_id",
            "exception_date",
            name="uq_shift_exceptions_company_shift_date",
        ),
    )
    op.create_index(
        "ix_shift_exceptions_company_date", "shift_exceptions", ["company_id", "exception_date"]
    )


def downgrade() -> None:
    op.drop_index("ix_shift_exceptions_company_date", table_name="shift_exceptions")
    op.drop_table("shift_exceptions")
    op.drop_index("ix_shift_assignments_branch_dates", table_name="shift_assignments")
    op.drop_index("ix_shift_assignments_employee_dates", table_name="shift_assignments")
    op.drop_table("shift_assignments")
    op.drop_index("ix_shifts_company_active", table_name="shifts")
    op.drop_table("shifts")
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_code IN ('shifts:view', 'shifts:manage')"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code IN ('shifts:view', 'shifts:manage')"))
