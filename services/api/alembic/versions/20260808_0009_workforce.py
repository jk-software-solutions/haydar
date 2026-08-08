"""tasks, notifications, leave, and documents

Revision ID: 20260808_0009
Revises: 20260808_0008
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0009"
down_revision: str | None = "20260808_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def company_fk() -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(["company_id"], ["companies.id"])


def member_fk(column: str, name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["company_id", column],
        ["company_memberships.company_id", "company_memberships.id"],
        name=name,
    )


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
        ("tasks:view", "View assigned tenant tasks"),
        ("tasks:manage", "Create and manage tenant tasks"),
        ("leave:view", "View tenant leave requests and balances"),
        ("leave:manage", "Manage leave types, balances, and approvals"),
        ("documents:view", "View tenant employee documents"),
        ("documents:manage", "Manage and review employee documents"),
    ]
    op.bulk_insert(
        permissions,
        [{"code": code, "description": description} for code, description in permission_rows],
    )
    grants = {
        "OWNER": tuple(code for code, _ in permission_rows),
        "MANAGER": tuple(code for code, _ in permission_rows),
        "HR_OFFICER": tuple(code for code, _ in permission_rows),
        "SUPERVISOR": ("tasks:view", "tasks:manage", "leave:view", "documents:view"),
        "EMPLOYEE": ("tasks:view", "leave:view", "documents:view"),
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
        "work_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(24), server_default="normal", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), server_default="new", nullable=False),
        sa.Column("completion_attachment_key", sa.String(500)),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        created_at(),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        company_fk(),
        member_fk("created_by_membership_id", "fk_work_tasks_company_creator"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "id", name="uq_work_tasks_company_id"),
    )
    op.create_index(
        "ix_work_tasks_company_status_due", "work_tasks", ["company_id", "status", "due_at"]
    )
    op.create_table(
        "task_assignees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True)),
        created_at(),
        company_fk(),
        sa.ForeignKeyConstraint(
            ["company_id", "task_id"],
            ["work_tasks.company_id", "work_tasks.id"],
            name="fk_task_assignees_company_task",
        ),
        member_fk("membership_id", "fk_task_assignees_company_membership"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "membership_id", name="uq_task_assignees_task_member"),
    )
    op.create_index("ix_task_assignees_member", "task_assignees", ["company_id", "membership_id"])
    op.create_table(
        "task_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("author_membership_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("attachment_key", sa.String(500)),
        created_at(),
        company_fk(),
        sa.ForeignKeyConstraint(
            ["company_id", "task_id"],
            ["work_tasks.company_id", "work_tasks.id"],
            name="fk_task_comments_company_task",
        ),
        member_fk("author_membership_id", "fk_task_comments_company_author"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_comments_task_created", "task_comments", ["task_id", "created_at"])
    op.create_table(
        "task_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("old_status", sa.String(32)),
        sa.Column("new_status", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text()),
        created_at(),
        company_fk(),
        sa.ForeignKeyConstraint(
            ["company_id", "task_id"],
            ["work_tasks.company_id", "work_tasks.id"],
            name="fk_task_history_company_task",
        ),
        member_fk("changed_by_membership_id", "fk_task_history_company_actor"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_history_task_created", "task_status_history", ["task_id", "created_at"]
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.String(1000), nullable=False),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", sa.Uuid()),
        sa.Column("urgent", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        created_at(),
        company_fk(),
        member_fk("membership_id", "fk_notifications_company_membership"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_member_unread",
        "notifications",
        ["company_id", "membership_id", "read_at"],
    )

    op.create_table(
        "leave_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("default_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_paid", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        created_at(),
        company_fk(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "id", name="uq_leave_types_company_id"),
        sa.UniqueConstraint("company_id", "code", name="uq_leave_types_company_code"),
    )
    op.create_table(
        "leave_balances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("leave_type_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("allocated_days", sa.Integer(), nullable=False),
        sa.Column("used_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        company_fk(),
        member_fk("membership_id", "fk_leave_balances_company_membership"),
        sa.ForeignKeyConstraint(
            ["company_id", "leave_type_id"],
            ["leave_types.company_id", "leave_types.id"],
            name="fk_leave_balances_company_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "membership_id", "leave_type_id", "year", name="uq_leave_balances_member_type_year"
        ),
    )
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("leave_type_id", sa.Uuid(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("attachment_key", sa.String(500)),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("reviewed_by_membership_id", sa.Uuid()),
        sa.Column("review_comment", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        created_at(),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        company_fk(),
        member_fk("membership_id", "fk_leave_requests_company_membership"),
        member_fk("reviewed_by_membership_id", "fk_leave_requests_company_reviewer"),
        sa.ForeignKeyConstraint(
            ["company_id", "leave_type_id"],
            ["leave_types.company_id", "leave_types.id"],
            name="fk_leave_requests_company_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leave_requests_company_status", "leave_requests", ["company_id", "status"])
    op.create_table(
        "employee_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("custom_type_name", sa.String(160)),
        sa.Column("document_number", sa.String(120)),
        sa.Column("issued_on", sa.Date()),
        sa.Column("expires_on", sa.Date()),
        sa.Column("attachment_key", sa.String(500), nullable=False),
        sa.Column("reminder_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("review_status", sa.String(24), server_default="pending_review", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        created_at(),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        company_fk(),
        member_fk("membership_id", "fk_employee_documents_company_membership"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_employee_documents_company_expiry", "employee_documents", ["company_id", "expires_on"]
    )


def downgrade() -> None:
    tables = [
        ("employee_documents", ["ix_employee_documents_company_expiry"]),
        ("leave_requests", ["ix_leave_requests_company_status"]),
        ("leave_balances", []),
        ("leave_types", []),
        ("notifications", ["ix_notifications_member_unread"]),
        ("task_status_history", ["ix_task_history_task_created"]),
        ("task_comments", ["ix_task_comments_task_created"]),
        ("task_assignees", ["ix_task_assignees_member"]),
        ("work_tasks", ["ix_work_tasks_company_status_due"]),
    ]
    for table, indexes in tables:
        for index in indexes:
            op.drop_index(index, table_name=table)
        op.drop_table(table)
    codes = (
        "'tasks:view','tasks:manage','leave:view','leave:manage',"
        "'documents:view','documents:manage'"
    )
    op.execute(sa.text(f"DELETE FROM role_permissions WHERE permission_code IN ({codes})"))
    op.execute(sa.text(f"DELETE FROM permissions WHERE code IN ({codes})"))
