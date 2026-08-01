"""employee device binding and change approval

Revision ID: 20260801_0004
Revises: 20260801_0003
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260801_0004"
down_revision: str | None = "20260801_0003"
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
    op.bulk_insert(
        permissions,
        [
            {
                "code": "devices:view",
                "description": "View company device registrations and change requests",
            },
            {
                "code": "devices:manage",
                "description": "Approve or reject employee device changes",
            },
        ],
    )
    op.bulk_insert(
        role_permissions,
        [
            {"role_code": "OWNER", "permission_code": "devices:view"},
            {"role_code": "OWNER", "permission_code": "devices:manage"},
            {"role_code": "MANAGER", "permission_code": "devices:view"},
            {"role_code": "MANAGER", "permission_code": "devices:manage"},
            {"role_code": "HR_OFFICER", "permission_code": "devices:view"},
            {"role_code": "HR_OFFICER", "permission_code": "devices:manage"},
            {"role_code": "SUPERVISOR", "permission_code": "devices:view"},
        ],
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("installation_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=24), nullable=False),
        sa.Column("device_name", sa.String(length=160), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("attestation_provider", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_membership_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_devices_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "approved_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_devices_company_approver",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_devices_company_membership",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
        sa.UniqueConstraint("company_id", "id", name="uq_devices_company_id"),
        sa.UniqueConstraint(
            "company_id", "installation_id", name="uq_devices_company_installation"
        ),
    )
    op.create_index(
        "ix_devices_company_membership",
        "devices",
        ["company_id", "membership_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_devices_company_membership_approved",
        "devices",
        ["company_id", "membership_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
    )
    op.create_table(
        "device_change_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("current_device_id", sa.Uuid(), nullable=True),
        sa.Column("requested_device_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reviewed_by_membership_id", sa.Uuid(), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_device_change_requests_company_id_companies"),
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_device_changes_company_membership",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "current_device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_device_changes_current_device",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "requested_device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_device_changes_requested_device",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "reviewed_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_device_changes_company_reviewer",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_device_change_requests")),
    )
    op.create_index(
        "ix_device_changes_company_status",
        "device_change_requests",
        ["company_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_device_changes_pending_membership",
        "device_change_requests",
        ["company_id", "membership_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_audit_logs_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "actor_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_audit_logs_company_actor",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(
        "ix_audit_logs_company_created",
        "audit_logs",
        ["company_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_company_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("uq_device_changes_pending_membership", table_name="device_change_requests")
    op.drop_index("ix_device_changes_company_status", table_name="device_change_requests")
    op.drop_table("device_change_requests")
    op.drop_index("uq_devices_company_membership_approved", table_name="devices")
    op.drop_index("ix_devices_company_membership", table_name="devices")
    op.drop_table("devices")
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_code IN "
            "('devices:view', 'devices:manage')"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code IN ('devices:view', 'devices:manage')"))
