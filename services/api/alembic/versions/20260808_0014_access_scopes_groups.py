"""Add granular access overrides, manager scopes, and organization groups.

Revision ID: 20260808_0014
Revises: 20260808_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0014"
down_revision: str | None = "20260808_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organization_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_organization_groups_company_id_companies")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_groups")),
        sa.UniqueConstraint("company_id", "code", name="uq_organization_groups_company_code"),
        sa.UniqueConstraint("company_id", "id", name="uq_organization_groups_company_id"),
    )
    op.create_index(
        "ix_organization_groups_company_active",
        "organization_groups",
        ["company_id", "is_active"],
        unique=False,
    )
    op.create_table(
        "employee_group_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id", "assigned_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_group_memberships_company_actor",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "group_id"],
            ["organization_groups.company_id", "organization_groups.id"],
            name="fk_employee_group_memberships_company_group",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_group_memberships_company_member",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_group_memberships")),
        sa.UniqueConstraint(
            "company_id", "group_id", "membership_id", name="uq_employee_group_memberships"
        ),
    )
    op.create_index(
        "ix_employee_group_memberships_member",
        "employee_group_memberships",
        ["company_id", "membership_id"],
        unique=False,
    )
    op.add_column("presence_requests", sa.Column("group_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_presence_requests_company_group",
        "presence_requests",
        "organization_groups",
        ["company_id", "group_id"],
        ["company_id", "id"],
    )
    op.create_table(
        "membership_permission_overrides",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("permission_code", sa.String(length=100), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("updated_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_membership_permission_overrides_company_member",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "updated_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_membership_permission_overrides_company_actor",
        ),
        sa.ForeignKeyConstraint(
            ["permission_code"], ["permissions.code"], name=op.f("fk_membership_permission_overrides_permission_code_permissions")
        ),
        sa.PrimaryKeyConstraint(
            "company_id", "membership_id", "permission_code", name=op.f("pk_membership_permission_overrides")
        ),
    )
    op.create_index(
        "ix_membership_permission_overrides_company",
        "membership_permission_overrides",
        ["company_id", "membership_id"],
        unique=False,
    )
    _create_scope_table("branch", "branches")
    _create_scope_table("department", "departments")
    _create_scope_table("group", "organization_groups")


def _create_scope_table(scope: str, target_table: str) -> None:
    table = f"membership_{scope}_scopes"
    target_column = f"{scope}_id"
    op.create_table(
        table,
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column(target_column, sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name=f"fk_{table}_company_member",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", target_column],
            [f"{target_table}.company_id", f"{target_table}.id"],
            name=f"fk_{table}_company_{scope}",
        ),
        sa.PrimaryKeyConstraint(
            "company_id", "membership_id", target_column, name=op.f(f"pk_{table}")
        ),
    )


def downgrade() -> None:
    op.drop_table("membership_group_scopes")
    op.drop_table("membership_department_scopes")
    op.drop_table("membership_branch_scopes")
    op.drop_constraint(
        "fk_presence_requests_company_group", "presence_requests", type_="foreignkey"
    )
    op.drop_column("presence_requests", "group_id")
    op.drop_index(
        "ix_membership_permission_overrides_company",
        table_name="membership_permission_overrides",
    )
    op.drop_table("membership_permission_overrides")
    op.drop_index(
        "ix_employee_group_memberships_member", table_name="employee_group_memberships"
    )
    op.drop_table("employee_group_memberships")
    op.drop_index("ix_organization_groups_company_active", table_name="organization_groups")
    op.drop_table("organization_groups")
