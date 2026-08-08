from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.identity import utc_now


class WorkTask(Base):
    __tablename__ = "work_tasks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "created_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_work_tasks_company_creator",
        ),
        ForeignKeyConstraint(
            ["company_id", "completion_attachment_file_id"],
            ["stored_files.company_id", "stored_files.id"],
            name="fk_work_tasks_company_completion_attachment",
        ),
        UniqueConstraint("company_id", "id", name="uq_work_tasks_company_id"),
        Index("ix_work_tasks_company_status_due", "company_id", "status", "due_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    created_by_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(24), default="normal", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    completion_attachment_file_id: Mapped[UUID | None]
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class TaskAssignee(Base):
    __tablename__ = "task_assignees"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "task_id"],
            ["work_tasks.company_id", "work_tasks.id"],
            name="fk_task_assignees_company_task",
        ),
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_task_assignees_company_membership",
        ),
        UniqueConstraint("task_id", "membership_id", name="uq_task_assignees_task_member"),
        Index("ix_task_assignees_member", "company_id", "membership_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    task_id: Mapped[UUID] = mapped_column(nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TaskComment(Base):
    __tablename__ = "task_comments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "task_id"],
            ["work_tasks.company_id", "work_tasks.id"],
            name="fk_task_comments_company_task",
        ),
        ForeignKeyConstraint(
            ["company_id", "author_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_task_comments_company_author",
        ),
        ForeignKeyConstraint(
            ["company_id", "attachment_file_id"],
            ["stored_files.company_id", "stored_files.id"],
            name="fk_task_comments_company_attachment",
        ),
        Index("ix_task_comments_task_created", "task_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    task_id: Mapped[UUID] = mapped_column(nullable=False)
    author_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_file_id: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TaskStatusHistory(Base):
    __tablename__ = "task_status_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "task_id"],
            ["work_tasks.company_id", "work_tasks.id"],
            name="fk_task_history_company_task",
        ),
        ForeignKeyConstraint(
            ["company_id", "changed_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_task_history_company_actor",
        ),
        Index("ix_task_history_task_created", "task_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    task_id: Mapped[UUID] = mapped_column(nullable=False)
    changed_by_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(32))
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_notifications_company_membership",
        ),
        Index("ix_notifications_member_unread", "company_id", "membership_id", "read_at"),
        UniqueConstraint("company_id", "id", name="uq_notifications_company_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(80))
    target_id: Mapped[UUID | None]
    urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_notification_preferences_company_member",
        ),
        UniqueConstraint("company_id", "membership_id", name="uq_notification_preferences_member"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    muted_kinds: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5))
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PushDeviceToken(Base):
    __tablename__ = "push_device_tokens"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_push_device_tokens_company_member",
        ),
        UniqueConstraint("token_hash", name="uq_push_device_tokens_hash"),
        UniqueConstraint("company_id", "id", name="uq_push_device_tokens_company_id"),
        Index("ix_push_device_tokens_member_active", "company_id", "membership_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    platform: Mapped[str] = mapped_column(String(24), nullable=False)
    token: Mapped[str] = mapped_column(String(4096), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    app_version: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_notification_deliveries_company_member",
        ),
        ForeignKeyConstraint(
            ["company_id", "notification_id"],
            ["notifications.company_id", "notifications.id"],
            name="fk_notification_deliveries_company_notification",
        ),
        ForeignKeyConstraint(
            ["company_id", "push_token_id"],
            ["push_device_tokens.company_id", "push_device_tokens.id"],
            name="fk_notification_deliveries_company_token",
        ),
        UniqueConstraint(
            "notification_id", "push_token_id", name="uq_notification_deliveries_target"
        ),
        Index("ix_notification_deliveries_status_retry", "status", "next_attempt_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    notification_id: Mapped[UUID] = mapped_column(nullable=False)
    push_token_id: Mapped[UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(500))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LeaveType(Base):
    __tablename__ = "leave_types"
    __table_args__ = (
        UniqueConstraint("company_id", "id", name="uq_leave_types_company_id"),
        UniqueConstraint("company_id", "code", name="uq_leave_types_company_code"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    default_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_leave_balances_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "leave_type_id"],
            ["leave_types.company_id", "leave_types.id"],
            name="fk_leave_balances_company_type",
        ),
        UniqueConstraint(
            "membership_id", "leave_type_id", "year", name="uq_leave_balances_member_type_year"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    leave_type_id: Mapped[UUID] = mapped_column(nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_days: Mapped[int] = mapped_column(Integer, nullable=False)
    used_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_leave_requests_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "leave_type_id"],
            ["leave_types.company_id", "leave_types.id"],
            name="fk_leave_requests_company_type",
        ),
        ForeignKeyConstraint(
            ["company_id", "reviewed_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_leave_requests_company_reviewer",
        ),
        ForeignKeyConstraint(
            ["company_id", "attachment_file_id"],
            ["stored_files.company_id", "stored_files.id"],
            name="fk_leave_requests_company_attachment",
        ),
        Index("ix_leave_requests_company_status", "company_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    leave_type_id: Mapped[UUID] = mapped_column(nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_file_id: Mapped[UUID | None]
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    reviewed_by_membership_id: Mapped[UUID | None]
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_documents_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "attachment_file_id"],
            ["stored_files.company_id", "stored_files.id"],
            name="fk_employee_documents_company_attachment",
        ),
        Index("ix_employee_documents_company_expiry", "company_id", "expires_on"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    custom_type_name: Mapped[str | None] = mapped_column(String(160))
    document_number: Mapped[str | None] = mapped_column(String(120))
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    attachment_file_id: Mapped[UUID] = mapped_column(nullable=False)
    reminder_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    review_status: Mapped[str] = mapped_column(String(24), default="pending_review", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
