"""Add explicit task extension request decisions.

Revision ID: 20260808_0022
Revises: 20260808_0021
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0022"
down_revision: str | None = "20260808_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_extension_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_membership_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_due_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("decided_by_membership_id", sa.Uuid()),
        sa.Column("decision_comment", sa.Text()),
        sa.Column("approved_due_at", sa.DateTime(timezone=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(
            ["company_id", "task_id"],
            ["work_tasks.company_id", "work_tasks.id"],
            name="fk_task_extension_requests_company_task",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "requested_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_task_extension_requests_company_requester",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "decided_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_task_extension_requests_company_decider",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_extension_requests_task_created",
        "task_extension_requests",
        ["task_id", "created_at"],
    )
    op.create_index(
        "uq_task_extension_requests_pending",
        "task_extension_requests",
        ["company_id", "task_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_task_extension_requests_pending", table_name="task_extension_requests"
    )
    op.drop_index(
        "ix_task_extension_requests_task_created", table_name="task_extension_requests"
    )
    op.drop_table("task_extension_requests")
