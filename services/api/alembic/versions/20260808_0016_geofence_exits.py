"""Add automatic geofence exit detection and review events.

Revision ID: 20260808_0016
Revises: 20260808_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0016"
down_revision: str | None = "20260808_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_permission_requests_company_id", "permission_requests", ["company_id", "id"]
    )
    op.create_table(
        "geofence_exit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("permission_request_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("location_permission", sa.String(length=32), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("accuracy_m", sa.Integer(), nullable=True),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        sa.Column("consecutive_outside_samples", sa.Integer(), nullable=False),
        sa.Column("grace_seconds", sa.Integer(), nullable=False),
        sa.Column("reconfirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_membership_id", sa.Uuid(), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_geofence_exit_events_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_geofence_exit_events_company_branch",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_geofence_exit_events_company_device",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_geofence_exit_events_company_member",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "permission_request_id"],
            ["permission_requests.company_id", "permission_requests.id"],
            name="fk_geofence_exit_events_company_permission",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "record_id"],
            ["attendance_records.company_id", "attendance_records.id"],
            name="fk_geofence_exit_events_company_record",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "reviewed_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_geofence_exit_events_company_reviewer",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "shift_id"],
            ["shifts.company_id", "shifts.id"],
            name="fk_geofence_exit_events_company_shift",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_geofence_exit_events")),
    )
    op.create_index(
        "ix_geofence_exit_events_company_detected",
        "geofence_exit_events",
        ["company_id", "detected_at"],
        unique=False,
    )
    op.create_index(
        "uq_geofence_exit_events_open_record",
        "geofence_exit_events",
        ["company_id", "record_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('observing', 'unauthorized')"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (code, description) VALUES
              ('geofence_exits:view', 'View unauthorized geofence exit events'),
              ('geofence_exits:manage', 'Review unauthorized geofence exit events')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_code, permission_code)
            SELECT role_code, permission_code
            FROM (VALUES
              ('OWNER', 'geofence_exits:view'),
              ('OWNER', 'geofence_exits:manage'),
              ('MANAGER', 'geofence_exits:view'),
              ('MANAGER', 'geofence_exits:manage'),
              ('HR_OFFICER', 'geofence_exits:view'),
              ('HR_OFFICER', 'geofence_exits:manage'),
              ('SUPERVISOR', 'geofence_exits:view'),
              ('SUPERVISOR', 'geofence_exits:manage')
            ) AS values_to_add(role_code, permission_code)
            ON CONFLICT (role_code, permission_code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_code IN "
            "('geofence_exits:view', 'geofence_exits:manage')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN "
            "('geofence_exits:view', 'geofence_exits:manage')"
        )
    )
    op.drop_index("uq_geofence_exit_events_open_record", table_name="geofence_exit_events")
    op.drop_index("ix_geofence_exit_events_company_detected", table_name="geofence_exit_events")
    op.drop_table("geofence_exit_events")
    op.drop_constraint(
        "uq_permission_requests_company_id", "permission_requests", type_="unique"
    )
