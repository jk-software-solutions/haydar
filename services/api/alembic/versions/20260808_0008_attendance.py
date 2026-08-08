"""attendance, permissions, and presence verification

Revision ID: 20260808_0008
Revises: 20260801_0007
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0008"
down_revision: str | None = "20260801_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    permissions = sa.table(
        "permissions", sa.column("code", sa.String), sa.column("description", sa.String)
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    permission_rows = [
        ("attendance:view", "View tenant attendance records"),
        ("attendance:manage", "Create and correct attendance records"),
        ("permissions:view", "View employee permission requests"),
        ("permissions:manage", "Review employee permission requests"),
        ("presence:manage", "Create and review presence requests"),
    ]
    op.bulk_insert(
        permissions, [{"code": code, "description": desc} for code, desc in permission_rows]
    )
    grants = {
        "OWNER": tuple(code for code, _ in permission_rows),
        "MANAGER": tuple(code for code, _ in permission_rows),
        "HR_OFFICER": tuple(code for code, _ in permission_rows),
        "SUPERVISOR": (
            "attendance:view",
            "permissions:view",
            "permissions:manage",
            "presence:manage",
        ),
        "EMPLOYEE": ("attendance:view", "permissions:view"),
    }
    op.bulk_insert(
        role_permissions,
        [
            {"role_code": role, "permission_code": permission}
            for role, role_grants in grants.items()
            for permission in role_grants
        ],
    )

    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True)),
        sa.Column("checked_out_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("check_in_method", sa.String(24)),
        sa.Column("check_out_method", sa.String(24)),
        sa.Column("late_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("early_departure_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("worked_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_manual", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("review_status", sa.String(24), server_default="accepted", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_attendance_records_company_membership",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_attendance_records_company_branch",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "shift_id"],
            ["shifts.company_id", "shifts.id"],
            name="fk_attendance_records_company_shift",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "id", name="uq_attendance_records_company_id"),
        sa.UniqueConstraint(
            "company_id", "membership_id", "work_date", name="uq_attendance_records_member_date"
        ),
    )
    op.create_index(
        "ix_attendance_records_company_date", "attendance_records", ["company_id", "work_date"]
    )
    op.create_index(
        "uq_attendance_records_open_member",
        "attendance_records",
        ["company_id", "membership_id"],
        unique=True,
        postgresql_where=sa.text("checked_in_at IS NOT NULL AND checked_out_at IS NULL"),
    )

    op.create_table(
        "attendance_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("actor_membership_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid()),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("method", sa.String(24), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column("distance_m", sa.Integer()),
        sa.Column("biometric_confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "record_id"],
            ["attendance_records.company_id", "attendance_records.id"],
            name="fk_attendance_events_company_record",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_attendance_events_company_device",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "actor_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_attendance_events_company_actor",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attendance_events_record_created", "attendance_events", ["record_id", "created_at"]
    )

    op.create_table(
        "branch_qr_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_branch_qr_tokens_company_branch",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "created_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_branch_qr_tokens_company_actor",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_branch_qr_tokens_company_expiry", "branch_qr_tokens", ["company_id", "expires_at"]
    )

    op.create_table(
        "permission_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("request_type", sa.String(32), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("attachment_key", sa.String(500)),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("reviewed_by_membership_id", sa.Uuid()),
        sa.Column("review_comment", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_permission_requests_company_membership",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "reviewed_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_permission_requests_company_reviewer",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_permission_requests_company_status", "permission_requests", ["company_id", "status"]
    )

    op.create_table(
        "presence_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid()),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), server_default="active", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "created_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_presence_requests_company_actor",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_presence_requests_company_branch",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "id", name="uq_presence_requests_company_id"),
    )
    op.create_index(
        "ix_presence_requests_company_deadline", "presence_requests", ["company_id", "deadline_at"]
    )

    op.create_table(
        "presence_recipients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("presence_request_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid()),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column("distance_m", sa.Integer()),
        sa.Column("note", sa.String(500)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "presence_request_id"],
            ["presence_requests.company_id", "presence_requests.id"],
            name="fk_presence_recipients_company_request",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_presence_recipients_company_membership",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_presence_recipients_company_device",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "presence_request_id", "membership_id", name="uq_presence_recipients_request_member"
        ),
    )
    op.create_index(
        "ix_presence_recipients_member_status", "presence_recipients", ["membership_id", "status"]
    )


def downgrade() -> None:
    for table, indexes in [
        ("presence_recipients", ["ix_presence_recipients_member_status"]),
        ("presence_requests", ["ix_presence_requests_company_deadline"]),
        ("permission_requests", ["ix_permission_requests_company_status"]),
        ("branch_qr_tokens", ["ix_branch_qr_tokens_company_expiry"]),
        ("attendance_events", ["ix_attendance_events_record_created"]),
        (
            "attendance_records",
            ["uq_attendance_records_open_member", "ix_attendance_records_company_date"],
        ),
    ]:
        for index in indexes:
            op.drop_index(index, table_name=table)
        op.drop_table(table)
    codes = (
        "'attendance:view','attendance:manage','permissions:view',"
        "'permissions:manage','presence:manage'"
    )
    op.execute(sa.text(f"DELETE FROM role_permissions WHERE permission_code IN ({codes})"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ({codes})"))
