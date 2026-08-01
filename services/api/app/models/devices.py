from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_devices_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "approved_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_devices_company_approver",
        ),
        UniqueConstraint("company_id", "id", name="uq_devices_company_id"),
        UniqueConstraint("company_id", "installation_id", name="uq_devices_company_installation"),
        Index("ix_devices_company_membership", "company_id", "membership_id", "status"),
        Index(
            "uq_devices_company_membership_approved",
            "company_id",
            "membership_id",
            unique=True,
            postgresql_where=text("status = 'approved'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    installation_id: Mapped[UUID] = mapped_column(nullable=False)
    platform: Mapped[str] = mapped_column(String(24), nullable=False)
    device_name: Mapped[str] = mapped_column(String(160), nullable=False)
    public_key: Mapped[str | None] = mapped_column(Text)
    attestation_provider: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_membership_id: Mapped[UUID | None] = mapped_column()
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class DeviceChangeRequest(Base):
    __tablename__ = "device_change_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_device_changes_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "current_device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_device_changes_current_device",
        ),
        ForeignKeyConstraint(
            ["company_id", "requested_device_id"],
            ["devices.company_id", "devices.id"],
            name="fk_device_changes_requested_device",
        ),
        ForeignKeyConstraint(
            ["company_id", "reviewed_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_device_changes_company_reviewer",
        ),
        Index("ix_device_changes_company_status", "company_id", "status"),
        Index(
            "uq_device_changes_pending_membership",
            "company_id",
            "membership_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    current_device_id: Mapped[UUID | None] = mapped_column()
    requested_device_id: Mapped[UUID] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    reviewed_by_membership_id: Mapped[UUID | None] = mapped_column()
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "actor_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_audit_logs_company_actor",
        ),
        Index("ix_audit_logs_company_created", "company_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    actor_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
