"""persistent role based access control

Revision ID: 20260801_0003
Revises: 20260801_0002
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0003"
down_revision: str | None = "20260801_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES = {
    "OWNER": "Company owner",
    "MANAGER": "Company manager",
    "SUPERVISOR": "Supervisor",
    "HR_OFFICER": "HR officer",
    "EMPLOYEE": "Employee",
}
PERMISSIONS = {
    "members:view": "View company memberships and invitations",
    "members:create": "Invite new company members",
    "members:manage": "Update company memberships and roles",
    "settings:manage": "Manage company settings",
}
ROLE_PERMISSIONS = {
    "OWNER": tuple(PERMISSIONS),
    "MANAGER": ("members:view", "members:create", "members:manage"),
    "HR_OFFICER": ("members:view", "members:create", "members:manage"),
    "SUPERVISOR": ("members:view",),
    "EMPLOYEE": (),
}


def upgrade() -> None:
    roles = op.create_table(
        "roles",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_roles")),
    )
    permissions = op.create_table(
        "permissions",
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_permissions")),
    )
    role_permissions = op.create_table(
        "role_permissions",
        sa.Column("role_code", sa.String(length=40), nullable=False),
        sa.Column("permission_code", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_code"],
            ["permissions.code"],
            name=op.f("fk_role_permissions_permission_code_permissions"),
        ),
        sa.ForeignKeyConstraint(
            ["role_code"],
            ["roles.code"],
            name=op.f("fk_role_permissions_role_code_roles"),
        ),
        sa.PrimaryKeyConstraint(
            "role_code",
            "permission_code",
            name=op.f("pk_role_permissions"),
        ),
    )
    op.create_table(
        "membership_roles",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("role_code", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_membership_roles_company_membership",
        ),
        sa.ForeignKeyConstraint(
            ["role_code"],
            ["roles.code"],
            name=op.f("fk_membership_roles_role_code_roles"),
        ),
        sa.PrimaryKeyConstraint(
            "company_id",
            "membership_id",
            "role_code",
            name=op.f("pk_membership_roles"),
        ),
    )
    op.create_index(
        "ix_membership_roles_company",
        "membership_roles",
        ["company_id", "role_code"],
        unique=False,
    )

    op.bulk_insert(
        roles,
        [
            {"code": code, "display_name": display_name, "is_system": True}
            for code, display_name in ROLES.items()
        ],
    )
    op.bulk_insert(
        permissions,
        [{"code": code, "description": description} for code, description in PERMISSIONS.items()],
    )
    op.bulk_insert(
        role_permissions,
        [
            {"role_code": role_code, "permission_code": permission_code}
            for role_code, permission_codes in ROLE_PERMISSIONS.items()
            for permission_code in permission_codes
        ],
    )
    op.execute(
        sa.text(
            """
            INSERT INTO membership_roles
                (company_id, membership_id, role_code, created_at)
            SELECT company_id, id, role_code, created_at
            FROM company_memberships
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_membership_roles_company", table_name="membership_roles")
    op.drop_table("membership_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
