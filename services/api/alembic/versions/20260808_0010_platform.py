"""reports, subscriptions, coupons, and platform administration

Revision ID: 20260808_0010
Revises: 20260808_0009
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0010"
down_revision: str | None = "20260808_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def now_column(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


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
        ("reports:view", "View tenant workforce reports"),
        ("reports:export", "Export tenant reports"),
        ("subscription:view", "View the company subscription"),
        ("subscription:manage", "Manage company subscription requests"),
    ]
    op.bulk_insert(
        permissions,
        [{"code": code, "description": description} for code, description in permission_rows],
    )
    grants = {
        "OWNER": tuple(code for code, _ in permission_rows),
        "MANAGER": tuple(code for code, _ in permission_rows),
        "HR_OFFICER": ("reports:view", "reports:export", "subscription:view"),
        "SUPERVISOR": ("reports:view",),
        "EMPLOYEE": ("subscription:view",),
    }
    op.bulk_insert(
        role_permissions,
        [
            {"role_code": role, "permission_code": code}
            for role, codes in grants.items()
            for code in codes
        ],
    )

    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("monthly_price", sa.Integer(), server_default="0", nullable=False),
        sa.Column("annual_price", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(3), server_default="SAR", nullable=False),
        sa.Column("limits", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("features", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("support_level", sa.String(40), server_default="standard", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        now_column("created_at"),
        now_column("updated_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    plans = sa.table(
        "subscription_plans",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("monthly_price", sa.Integer),
        sa.column("annual_price", sa.Integer),
        sa.column("currency", sa.String),
        sa.column("limits", sa.JSON),
        sa.column("features", sa.JSON),
        sa.column("support_level", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    from uuid import UUID

    op.bulk_insert(
        plans,
        [
            {
                "id": UUID("10000000-0000-0000-0000-000000000001"),
                "code": "FREE_TRIAL",
                "name": "Free Trial",
                "description": "Evaluation plan",
                "monthly_price": 0,
                "annual_price": 0,
                "currency": "SAR",
                "limits": {"employees": 10, "branches": 1, "storage_mb": 100},
                "features": {
                    "gps": True,
                    "qr": False,
                    "tasks": True,
                    "documents": False,
                    "reports": "basic",
                },
                "support_level": "community",
                "is_active": True,
            },
            {
                "id": UUID("10000000-0000-0000-0000-000000000002"),
                "code": "BASIC",
                "name": "Basic",
                "description": "Small teams",
                "monthly_price": 19900,
                "annual_price": 199000,
                "currency": "SAR",
                "limits": {"employees": 50, "branches": 3, "storage_mb": 2048},
                "features": {
                    "gps": True,
                    "qr": True,
                    "tasks": True,
                    "documents": True,
                    "reports": "basic",
                },
                "support_level": "standard",
                "is_active": True,
            },
            {
                "id": UUID("10000000-0000-0000-0000-000000000003"),
                "code": "PROFESSIONAL",
                "name": "Professional",
                "description": "Growing organizations",
                "monthly_price": 49900,
                "annual_price": 499000,
                "currency": "SAR",
                "limits": {"employees": 250, "branches": 20, "storage_mb": 10240},
                "features": {
                    "gps": True,
                    "qr": True,
                    "tasks": True,
                    "documents": True,
                    "reports": "advanced",
                },
                "support_level": "priority",
                "is_active": True,
            },
            {
                "id": UUID("10000000-0000-0000-0000-000000000004"),
                "code": "ENTERPRISE",
                "name": "Enterprise",
                "description": "Custom enterprise plan",
                "monthly_price": 0,
                "annual_price": 0,
                "currency": "SAR",
                "limits": {"employees": 1000000, "branches": 1000000, "storage_mb": 1000000},
                "features": {
                    "gps": True,
                    "qr": True,
                    "tasks": True,
                    "documents": True,
                    "reports": "advanced",
                },
                "support_level": "dedicated",
                "is_active": True,
            },
        ],
    )
    op.create_table(
        "company_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("billing_cycle", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("activated_by_membership_id", sa.Uuid()),
        sa.Column("activation_note", sa.Text()),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        now_column("created_at"),
        now_column("updated_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "activated_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_company_subscriptions_company_actor",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_company_subscriptions_company_status", "company_subscriptions", ["company_id", "status"]
    )
    op.create_table(
        "coupons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("discount_type", sa.String(16), nullable=False),
        sa.Column("discount_value", sa.Integer(), nullable=False),
        sa.Column("max_redemptions", sa.Integer()),
        sa.Column("redeemed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        now_column("created_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("coupon_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid()),
        now_column("redeemed_at"),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["company_subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coupon_id", "company_id", name="uq_coupon_company"),
    )
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("report_type", sa.String(40), nullable=False),
        sa.Column("export_format", sa.String(12), nullable=False),
        sa.Column("filters", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("progress_percent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("filename", sa.String(255)),
        sa.Column("content_type", sa.String(120)),
        sa.Column("file_content", sa.LargeBinary()),
        sa.Column("error_message", sa.String(1000)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        now_column("created_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "requested_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_export_jobs_company_requester",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_jobs_company_created", "export_jobs", ["company_id", "created_at"])
    op.create_table(
        "support_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("platform_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        now_column("started_at"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["platform_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("value", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid()),
        now_column("updated_at"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "platform_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("details", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        now_column("created_at"),
        sa.ForeignKeyConstraint(["platform_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_audit_logs_created", "platform_audit_logs", ["created_at"])
    op.create_table(
        "attendance_leaderboard_settings",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("visibility", sa.String(24), server_default="disabled", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        now_column("updated_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("company_id"),
    )


def downgrade() -> None:
    for table, indexes in [
        ("attendance_leaderboard_settings", []),
        ("platform_audit_logs", ["ix_platform_audit_logs_created"]),
        ("platform_settings", []),
        ("support_sessions", []),
        ("export_jobs", ["ix_export_jobs_company_created"]),
        ("coupon_redemptions", []),
        ("coupons", []),
        ("company_subscriptions", ["ix_company_subscriptions_company_status"]),
        ("subscription_plans", []),
    ]:
        for index in indexes:
            op.drop_index(index, table_name=table)
        op.drop_table(table)
    codes = "'reports:view','reports:export','subscription:view','subscription:manage'"
    op.execute(sa.text(f"DELETE FROM role_permissions WHERE permission_code IN ({codes})"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ({codes})"))
