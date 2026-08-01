"""tenant branches departments and transfer history

Revision ID: 20260801_0006
Revises: 20260801_0005
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0006"
down_revision: str | None = "20260801_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("description", sa.String),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    permission_rows = [
        ("branches:view", "View company branches"),
        ("branches:manage", "Create and update company branches"),
        ("departments:view", "View company departments"),
        ("departments:manage", "Create and update company departments"),
        ("assignments:view", "View employee branch assignment history"),
        ("assignments:manage", "Assign and transfer employees between branches"),
    ]
    op.bulk_insert(
        permissions,
        [{"code": code, "description": description} for code, description in permission_rows],
    )
    role_grants = {
        "OWNER": [code for code, _ in permission_rows],
        "MANAGER": [code for code, _ in permission_rows],
        "HR_OFFICER": [code for code, _ in permission_rows],
        "SUPERVISOR": ["branches:view", "departments:view", "assignments:view"],
        "EMPLOYEE": ["branches:view", "departments:view"],
    }
    op.bulk_insert(
        role_permissions,
        [
            {"role_code": role_code, "permission_code": permission_code}
            for role_code, permission_codes in role_grants.items()
            for permission_code in permission_codes
        ],
    )

    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("parent_department_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_departments_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "parent_department_id"],
            ["departments.company_id", "departments.id"],
            name="fk_departments_company_parent",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("company_id", "code", name="uq_departments_company_code"),
        sa.UniqueConstraint("company_id", "id", name="uq_departments_company_id"),
    )
    op.create_index("ix_departments_company_active", "departments", ["company_id", "is_active"])

    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("manager_membership_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("saudi_short_address", sa.String(length=32), nullable=True),
        sa.Column("full_address", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("geofence_radius_m", sa.Integer(), server_default="100", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Riyadh", nullable=False),
        sa.Column("working_hours", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_branches_latitude_range"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_branches_longitude_range"),
        sa.CheckConstraint(
            "geofence_radius_m BETWEEN 20 AND 10000", name="ck_branches_geofence_radius"
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_branches_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "manager_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_branches_company_manager",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_branches")),
        sa.UniqueConstraint("company_id", "code", name="uq_branches_company_code"),
        sa.UniqueConstraint("company_id", "id", name="uq_branches_company_id"),
    )
    op.create_index("ix_branches_company_active", "branches", ["company_id", "is_active"])

    op.add_column("employee_profiles", sa.Column("department_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_employee_profiles_company_department",
        "employee_profiles",
        "departments",
        ["company_id", "department_id"],
        ["company_id", "id"],
    )

    op.create_table(
        "employee_branch_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_employee_branch_assignments_date_order",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_employee_branch_assignments_company_id_companies"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_branch_assignments_company_membership",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_employee_branch_assignments_company_branch",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "assigned_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_branch_assignments_company_actor",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_branch_assignments")),
    )
    op.create_index(
        "ix_employee_branch_assignments_history",
        "employee_branch_assignments",
        ["company_id", "membership_id", "effective_from"],
    )
    op.create_index(
        "uq_employee_branch_assignments_current",
        "employee_branch_assignments",
        ["company_id", "membership_id"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_employee_branch_assignments_current", table_name="employee_branch_assignments"
    )
    op.drop_index(
        "ix_employee_branch_assignments_history", table_name="employee_branch_assignments"
    )
    op.drop_table("employee_branch_assignments")
    op.drop_constraint(
        "fk_employee_profiles_company_department", "employee_profiles", type_="foreignkey"
    )
    op.drop_column("employee_profiles", "department_id")
    op.drop_index("ix_branches_company_active", table_name="branches")
    op.drop_table("branches")
    op.drop_index("ix_departments_company_active", table_name="departments")
    op.drop_table("departments")
    permission_codes = [
        "branches:view",
        "branches:manage",
        "departments:view",
        "departments:manage",
        "assignments:view",
        "assignments:manage",
    ]
    quoted = ", ".join(f"'{code}'" for code in permission_codes)
    op.execute(sa.text(f"DELETE FROM role_permissions WHERE permission_code IN ({quoted})"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ({quoted})"))
