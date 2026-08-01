from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.identity import utc_now


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "parent_department_id"],
            ["departments.company_id", "departments.id"],
            name="fk_departments_company_parent",
        ),
        UniqueConstraint("company_id", "id", name="uq_departments_company_id"),
        UniqueConstraint("company_id", "code", name="uq_departments_company_code"),
        Index("ix_departments_company_active", "company_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    parent_department_id: Mapped[UUID | None]
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "manager_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_branches_company_manager",
        ),
        UniqueConstraint("company_id", "id", name="uq_branches_company_id"),
        UniqueConstraint("company_id", "code", name="uq_branches_company_code"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        CheckConstraint(
            "geofence_radius_m BETWEEN 20 AND 10000",
            name="geofence_radius",
        ),
        Index("ix_branches_company_active", "company_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    manager_membership_id: Mapped[UUID | None]
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    saudi_short_address: Mapped[str | None] = mapped_column(String(32))
    full_address: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    geofence_radius_m: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Riyadh", nullable=False)
    working_hours: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_profiles_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "department_id"],
            ["departments.company_id", "departments.id"],
            name="fk_employee_profiles_company_department",
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
    department_id: Mapped[UUID | None]
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


class EmployeeBranchAssignment(Base):
    __tablename__ = "employee_branch_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_branch_assignments_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_employee_branch_assignments_company_branch",
        ),
        ForeignKeyConstraint(
            ["company_id", "assigned_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_employee_branch_assignments_company_actor",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="date_order",
        ),
        Index(
            "uq_employee_branch_assignments_current",
            "company_id",
            "membership_id",
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
        ),
        Index(
            "ix_employee_branch_assignments_history",
            "company_id",
            "membership_id",
            "effective_from",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    assigned_by_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Shift(Base):
    __tablename__ = "shifts"
    __table_args__ = (
        UniqueConstraint("company_id", "id", name="uq_shifts_company_id"),
        UniqueConstraint("company_id", "code", name="uq_shifts_company_code"),
        CheckConstraint("grace_period_minutes BETWEEN 0 AND 240", name="grace_range"),
        CheckConstraint("break_duration_minutes BETWEEN 0 AND 720", name="break_range"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="effective_date_order",
        ),
        Index("ix_shifts_company_active", "company_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_overnight: Mapped[bool] = mapped_column(Boolean, nullable=False)
    working_days: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    break_duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    recurrence: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "shift_id"],
            ["shifts.company_id", "shifts.id"],
            name="fk_shift_assignments_company_shift",
        ),
        ForeignKeyConstraint(
            ["company_id", "membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_shift_assignments_company_membership",
        ),
        ForeignKeyConstraint(
            ["company_id", "branch_id"],
            ["branches.company_id", "branches.id"],
            name="fk_shift_assignments_company_branch",
        ),
        ForeignKeyConstraint(
            ["company_id", "assigned_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_shift_assignments_company_actor",
        ),
        CheckConstraint(
            "(membership_id IS NULL) <> (branch_id IS NULL)",
            name="one_target",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="date_order",
        ),
        Index(
            "ix_shift_assignments_employee_dates",
            "company_id",
            "membership_id",
            "effective_from",
            "effective_to",
        ),
        Index(
            "ix_shift_assignments_branch_dates",
            "company_id",
            "branch_id",
            "effective_from",
            "effective_to",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    shift_id: Mapped[UUID] = mapped_column(nullable=False)
    membership_id: Mapped[UUID | None]
    branch_id: Mapped[UUID | None]
    assigned_by_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ShiftException(Base):
    __tablename__ = "shift_exceptions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "shift_id"],
            ["shifts.company_id", "shifts.id"],
            name="fk_shift_exceptions_company_shift",
        ),
        UniqueConstraint(
            "company_id",
            "shift_id",
            "exception_date",
            name="uq_shift_exceptions_company_shift_date",
        ),
        Index("ix_shift_exceptions_company_date", "company_id", "exception_date"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    shift_id: Mapped[UUID] = mapped_column(nullable=False)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_working_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    override_start_time: Mapped[time | None] = mapped_column(Time)
    override_end_time: Mapped[time | None] = mapped_column(Time)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
