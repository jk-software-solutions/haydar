from datetime import date, datetime
from decimal import Decimal
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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.identity import utc_now


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_attendance_records_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_attendance_records_company_branch",
        ),
        ForeignKeyConstraint(
            ["company_id", "shift_id"],
            ["shifts.company_id", "shifts.id"],
            name="fk_attendance_records_company_shift",
        ),
        UniqueConstraint("company_id", "id", name="uq_attendance_records_company_id"),
        UniqueConstraint(
            "company_id",
            "membership_id",
            "work_date",
            name="uq_attendance_records_member_date",
        ),
        Index("ix_attendance_records_company_date", "company_id", "work_date"),
        Index(
            "uq_attendance_records_open_member",
            "company_id",
            "membership_id",
            unique=True,
            postgresql_where=text("checked_in_at IS NOT NULL AND checked_out_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    shift_id: Mapped[UUID] = mapped_column(nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    check_in_method: Mapped[str | None] = mapped_column(String(24))
    check_out_method: Mapped[str | None] = mapped_column(String(24))
    late_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    early_departure_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    worked_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_status: Mapped[str] = mapped_column(String(24), default="accepted", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "record_id"],
            ["attendance_records.company_id", "attendance_records.id"],
            name="fk_attendance_events_company_record",
        ),
        ForeignKeyConstraint(
            ["company_id", "device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_attendance_events_company_device",
        ),
        ForeignKeyConstraint(
            ["company_id", "actor_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_attendance_events_company_actor",
        ),
        Index("ix_attendance_events_record_created", "record_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    record_id: Mapped[UUID] = mapped_column(nullable=False)
    actor_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    device_id: Mapped[UUID | None]
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    method: Mapped[str] = mapped_column(String(24), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    distance_m: Mapped[int | None] = mapped_column(Integer)
    biometric_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BranchQrToken(Base):
    __tablename__ = "branch_qr_tokens"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_branch_qr_tokens_company_branch",
        ),
        ForeignKeyConstraint(
            ["company_id", "created_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_branch_qr_tokens_company_actor",
        ),
        Index("ix_branch_qr_tokens_company_expiry", "company_id", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    created_by_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PermissionRequest(Base):
    __tablename__ = "permission_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_permission_requests_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "reviewed_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_permission_requests_company_reviewer",
        ),
        Index("ix_permission_requests_company_status", "company_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_key: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    reviewed_by_membership_id: Mapped[UUID | None]
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PresenceRequest(Base):
    __tablename__ = "presence_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "created_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_presence_requests_company_actor",
        ),
        ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_presence_requests_company_branch",
        ),
        UniqueConstraint("company_id", "id", name="uq_presence_requests_company_id"),
        Index("ix_presence_requests_company_deadline", "company_id", "deadline_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    created_by_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID | None]
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PresenceRecipient(Base):
    __tablename__ = "presence_recipients"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "presence_request_id"],
            ["presence_requests.company_id", "presence_requests.id"],
            name="fk_presence_recipients_company_request",
        ),
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_presence_recipients_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_presence_recipients_company_device",
        ),
        UniqueConstraint(
            "presence_request_id", "membership_id", name="uq_presence_recipients_request_member"
        ),
        Index("ix_presence_recipients_member_status", "membership_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    presence_request_id: Mapped[UUID] = mapped_column(nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    device_id: Mapped[UUID | None]
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    distance_m: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
