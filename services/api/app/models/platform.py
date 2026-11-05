from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.identity import utc_now


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    monthly_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    annual_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="SAR", nullable=False)
    limits: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    features: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    support_level: Mapped[str] = mapped_column(String(40), default="standard", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class CompanySubscription(Base):
    __tablename__ = "company_subscriptions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "activated_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_company_subscriptions_company_actor",
        ),
        Index("ix_company_subscriptions_company_status", "company_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Optional per-company overrides let the platform owner sell a custom
    # seat/branch/storage allowance without creating a one-off plan.
    limits_override: Mapped[dict[str, object] | None] = mapped_column(JSON)
    activated_by_membership_id: Mapped[UUID | None]
    activation_note: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class SubscriptionRequest(Base):
    """A customer request awaiting manual payment/activation approval."""

    __tablename__ = "subscription_requests"
    __table_args__ = (
        Index("ix_subscription_requests_company_status", "company_id", "status"),
        Index("ix_subscription_requests_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    requested_by_membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("company_memberships.id"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_subscription_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("company_subscriptions.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("subscription_plans.id"))
    billing_cycle: Mapped[str | None] = mapped_column(String(16))
    max_redemptions: Mapped[int | None] = mapped_column(Integer)
    redeemed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"
    __table_args__ = (UniqueConstraint("coupon_id", "company_id", name="uq_coupon_company"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    coupon_id: Mapped[UUID] = mapped_column(ForeignKey("coupons.id"), nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    subscription_id: Mapped[UUID | None] = mapped_column(ForeignKey("company_subscriptions.id"))
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "requested_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_export_jobs_company_requester",
        ),
        Index("ix_export_jobs_company_created", "company_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    requested_by_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    export_format: Mapped[str] = mapped_column(String(12), nullable=False)
    filters: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(120))
    file_content: Mapped[bytes | None] = mapped_column(LargeBinary)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utc_now() + timedelta(days=7), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SupportSession(Base):
    __tablename__ = "support_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    platform_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class PlatformAuditLog(Base):
    __tablename__ = "platform_audit_logs"
    __table_args__ = (Index("ix_platform_audit_logs_created", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    platform_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AttendanceLeaderboardSetting(Base):
    __tablename__ = "attendance_leaderboard_settings"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), primary_key=True)
    visibility: Mapped[str] = mapped_column(String(24), default="disabled", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anonymize: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
