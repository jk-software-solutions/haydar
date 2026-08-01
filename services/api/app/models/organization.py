from datetime import date, datetime
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
