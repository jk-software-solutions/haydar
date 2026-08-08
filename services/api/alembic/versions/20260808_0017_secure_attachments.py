"""Replace arbitrary attachment keys with protected stored-file relations.

Revision ID: 20260808_0017
Revises: 20260808_0016
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260808_0017"
down_revision: str | None = "20260808_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_COLUMNS = (
    ("work_tasks", "completion_attachment_key", "completion_attachment_file_id"),
    ("task_comments", "attachment_key", "attachment_file_id"),
    ("permission_requests", "attachment_key", "attachment_file_id"),
    ("leave_requests", "attachment_key", "attachment_file_id"),
    ("employee_documents", "attachment_key", "attachment_file_id"),
)


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_stored_files_company_id", "stored_files", ["company_id", "id"]
    )
    op.add_column("attendance_events", sa.Column("attachment_file_id", sa.Uuid()))
    for table, old_column, new_column in TABLE_COLUMNS:
        op.add_column(table, sa.Column(new_column, sa.Uuid()))
        op.execute(
            sa.text(
                f"""
                UPDATE {table} AS target
                SET {new_column} = files.id
                FROM stored_files AS files
                WHERE target.company_id = files.company_id
                  AND target.{old_column} = files.id::text
                """
            )
        )
    constraints = (
        ("attendance_events", "attachment_file_id", "fk_attendance_events_company_attachment"),
        (
            "work_tasks",
            "completion_attachment_file_id",
            "fk_work_tasks_company_completion_attachment",
        ),
        ("task_comments", "attachment_file_id", "fk_task_comments_company_attachment"),
        (
            "permission_requests",
            "attachment_file_id",
            "fk_permission_requests_company_attachment",
        ),
        ("leave_requests", "attachment_file_id", "fk_leave_requests_company_attachment"),
        (
            "employee_documents",
            "attachment_file_id",
            "fk_employee_documents_company_attachment",
        ),
    )
    for table, column, name in constraints:
        op.create_foreign_key(
            name,
            table,
            "stored_files",
            ["company_id", column],
            ["company_id", "id"],
        )
    for table, old_column, _new_column in TABLE_COLUMNS:
        op.drop_column(table, old_column)


def downgrade() -> None:
    for table, old_column, new_column in TABLE_COLUMNS:
        op.add_column(table, sa.Column(old_column, sa.String(500)))
        op.execute(
            sa.text(
                f"UPDATE {table} SET {old_column} = {new_column}::text "
                f"WHERE {new_column} IS NOT NULL"
            )
        )
    constraints = (
        ("employee_documents", "fk_employee_documents_company_attachment"),
        ("leave_requests", "fk_leave_requests_company_attachment"),
        ("permission_requests", "fk_permission_requests_company_attachment"),
        ("task_comments", "fk_task_comments_company_attachment"),
        ("work_tasks", "fk_work_tasks_company_completion_attachment"),
        ("attendance_events", "fk_attendance_events_company_attachment"),
    )
    for table, name in constraints:
        op.drop_constraint(name, table, type_="foreignkey")
    op.drop_column("attendance_events", "attachment_file_id")
    for table, _old_column, new_column in TABLE_COLUMNS:
        op.drop_column(table, new_column)
    op.drop_constraint("uq_stored_files_company_id", "stored_files", type_="unique")
