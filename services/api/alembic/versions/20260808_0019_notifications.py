"""Add push tokens, preferences, and durable notification delivery state.

Revision ID: 20260808_0019
Revises: 20260808_0018
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0019"
down_revision: str | None = "20260808_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_notifications_company_id", "notifications", ["company_id", "id"]
    )
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("muted_kinds", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("quiet_hours_start", sa.String(5)),
        sa.Column("quiet_hours_end", sa.String(5)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_notification_preferences_company_member",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "membership_id", name="uq_notification_preferences_member"
        ),
    )
    op.create_table(
        "push_device_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(24), nullable=False),
        sa.Column("token", sa.String(4096), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("app_version", sa.String(40)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_push_device_tokens_company_member",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_push_device_tokens_hash"),
        sa.UniqueConstraint("company_id", "id", name="uq_push_device_tokens_company_id"),
    )
    op.create_index(
        "ix_push_device_tokens_member_active",
        "push_device_tokens",
        ["company_id", "membership_id", "is_active"],
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("push_token_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("provider_message_id", sa.String(500)),
        sa.Column("last_error", sa.String(1000)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_notification_deliveries_company_member",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "notification_id"],
            ["notifications.company_id", "notifications.id"],
            name="fk_notification_deliveries_company_notification",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "push_token_id"],
            ["push_device_tokens.company_id", "push_device_tokens.id"],
            name="fk_notification_deliveries_company_token",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "notification_id", "push_token_id", name="uq_notification_deliveries_target"
        ),
    )
    op.create_index(
        "ix_notification_deliveries_status_retry",
        "notification_deliveries",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_deliveries_status_retry", table_name="notification_deliveries"
    )
    op.drop_table("notification_deliveries")
    op.drop_index("ix_push_device_tokens_member_active", table_name="push_device_tokens")
    op.drop_table("push_device_tokens")
    op.drop_table("notification_preferences")
    op.drop_constraint("uq_notifications_company_id", "notifications", type_="unique")
