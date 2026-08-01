from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.identity import utc_now


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_profiles_company_membership",
        ),
        UniqueConstraint(
            "company_id",
            "membership_id",
            name="uq_employee_profiles_company_membership",
        ),
        UniqueConstraint(
            "company_id",
            "employee_number",
            name="uq_employee_profiles_company_employee_number",
        ),
        Index("ix_employee_profiles_company_active", "company_id", "attendance_enabled"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    employee_number: Mapped[str | None] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(32))
    job_title: Mapped[str | None] = mapped_column(String(120))
    employment_type: Mapped[str] = mapped_column(String(32), default="full_time", nullable=False)
    hire_date: Mapped[date | None] = mapped_column(Date)
    preferred_locale: Mapped[str] = mapped_column(String(8), default="ar", nullable=False)
    attendance_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
