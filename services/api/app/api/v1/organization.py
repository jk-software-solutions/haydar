from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    require_department_scope,
    require_membership_scope,
    require_permission,
    tenant_context,
    visible_membership_ids,
)
from app.core.errors import ProblemError
from app.core.phone import normalize_e164
from app.db.session import get_session
from app.models.devices import AuditLog, Device
from app.models.identity import Company, CompanyMembership, RefreshSession, User
from app.models.organization import Department, EmployeeProfile

companies_router = APIRouter()
employees_router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


class CompanySettingsResponse(BaseModel):
    id: UUID
    technical_name: str
    display_name: str
    status: str
    default_locale: str
    timezone: str
    country_code: str
    version: int


class UpdateCompanySettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    default_locale: Literal["ar", "en"] | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    country_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z]{2}$",
    )

    @field_validator("display_name", "timezone")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for field_name in {"display_name", "default_locale", "timezone", "country_code"}:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class EmployeeResponse(BaseModel):
    id: UUID
    membership_id: UUID
    department_id: UUID | None
    display_name: str
    email: str
    role_code: str
    membership_status: str
    membership_version: int
    employee_number: str | None
    phone: str | None
    phone_login_enabled: bool
    job_title: str | None
    employment_type: str
    hire_date: date | None
    preferred_locale: str
    attendance_enabled: bool
    version: int
    created_at: datetime
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    page: int
    page_size: int
    total: int


class UpdateEmployeeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    employee_number: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    job_title: str | None = Field(default=None, max_length=120)
    employment_type: Literal["full_time", "part_time", "contractor", "temporary"] | None = None
    hire_date: date | None = None
    preferred_locale: Literal["ar", "en"] | None = None
    attendance_enabled: bool | None = None
    department_id: UUID | None = None

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("employee_number", "job_title")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return normalize_e164(value)

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for field_name in {
            "display_name",
            "employment_type",
            "preferred_locale",
            "attendance_enabled",
        }:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class UpdateEmployeeStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    status: Literal["active", "inactive"]
    reason: str = Field(min_length=3, max_length=1000)


def company_response(company: Company) -> CompanySettingsResponse:
    return CompanySettingsResponse(
        id=company.id,
        technical_name=company.technical_name,
        display_name=company.display_name,
        status=company.status,
        default_locale=company.default_locale,
        timezone=company.timezone,
        country_code=company.country_code,
        version=company.version,
    )


def employee_response(
    profile: EmployeeProfile,
    membership: CompanyMembership,
    user: User,
) -> EmployeeResponse:
    return EmployeeResponse(
        id=profile.id,
        membership_id=profile.membership_id,
        department_id=profile.department_id,
        display_name=profile.display_name,
        email=user.email,
        role_code=membership.role_code,
        membership_status=membership.status,
        membership_version=membership.version,
        employee_number=profile.employee_number,
        phone=profile.phone,
        phone_login_enabled=(
            user.phone_e164 == profile.phone and user.phone_verified_at is not None
        ),
        job_title=profile.job_title,
        employment_type=profile.employment_type,
        hire_date=profile.hire_date,
        preferred_locale=profile.preferred_locale,
        attendance_enabled=profile.attendance_enabled,
        version=profile.version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def employee_statement(company_id: UUID) -> Any:
    return (
        select(EmployeeProfile, CompanyMembership, User)
        .join(
            CompanyMembership,
            and_(
                CompanyMembership.company_id == EmployeeProfile.company_id,
                CompanyMembership.id == EmployeeProfile.membership_id,
            ),
        )
        .join(User, User.id == CompanyMembership.user_id)
        .where(EmployeeProfile.company_id == company_id)
    )


@companies_router.get("/current", response_model=CompanySettingsResponse)
async def get_company_settings(auth_session: CurrentAuthSession) -> CompanySettingsResponse:
    context = tenant_context(auth_session)
    return company_response(context.company)


@companies_router.patch("/current", response_model=CompanySettingsResponse)
async def update_company_settings(
    payload: UpdateCompanySettingsRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> CompanySettingsResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SETTINGS_MANAGE)
    company = await session.scalar(
        select(Company).where(Company.id == context.company_id).with_for_update()
    )
    if company is None:
        raise RuntimeError("Authenticated company no longer exists")
    if company.version != payload.version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Company settings changed",
            detail="Reload company settings before saving again.",
        )
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    for field_name, value in changes.items():
        setattr(company, field_name, value)
    company.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="company.settings.updated",
            target_type="company",
            target_id=company.id,
            details={"changed_fields": sorted(changes)},
        )
    )
    await session.commit()
    await session.refresh(company)
    return company_response(company)


@employees_router.get("/me", response_model=EmployeeResponse)
async def get_my_employee_profile(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> EmployeeResponse:
    context = tenant_context(auth_session)
    row = (
        await session.execute(
            employee_statement(context.company_id).where(
                EmployeeProfile.membership_id == context.membership.id
            )
        )
    ).one_or_none()
    if row is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="employee_not_found",
            title="Employee profile not found",
            detail="The employee profile does not exist in the current company.",
        )
    return employee_response(*row)


@employees_router.get("", response_model=EmployeeListResponse)
async def list_employees(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
) -> EmployeeListResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.MEMBERS_VIEW)
    statement = employee_statement(context.company_id)
    count_statement = (
        select(func.count())
        .select_from(EmployeeProfile)
        .where(EmployeeProfile.company_id == context.company_id)
    )
    visible = await visible_membership_ids(session, context)
    if visible is not None:
        statement = statement.where(EmployeeProfile.membership_id.in_(visible))
        count_statement = count_statement.where(EmployeeProfile.membership_id.in_(visible))
    if search is not None:
        pattern = f"%{search.strip()}%"
        criterion = or_(
            EmployeeProfile.display_name.ilike(pattern),
            EmployeeProfile.employee_number.ilike(pattern),
            User.email.ilike(pattern),
        )
        statement = statement.where(criterion)
        count_statement = (
            count_statement.join(
                CompanyMembership,
                and_(
                    CompanyMembership.company_id == EmployeeProfile.company_id,
                    CompanyMembership.id == EmployeeProfile.membership_id,
                ),
            )
            .join(User, User.id == CompanyMembership.user_id)
            .where(criterion)
        )
    total = await session.scalar(count_statement)
    rows = (
        await session.execute(
            statement.order_by(EmployeeProfile.display_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return EmployeeListResponse(
        items=[employee_response(*row) for row in rows],
        page=page,
        page_size=page_size,
        total=total or 0,
    )


@employees_router.get("/{membership_id}", response_model=EmployeeResponse)
async def get_employee(
    membership_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> EmployeeResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.MEMBERS_VIEW)
    await require_membership_scope(session, context, membership_id)
    row = (
        await session.execute(
            employee_statement(context.company_id).where(
                EmployeeProfile.membership_id == membership_id
            )
        )
    ).one_or_none()
    if row is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="employee_not_found",
            title="Employee profile not found",
            detail="The employee profile does not exist in the current company.",
        )
    return employee_response(*row)


@employees_router.patch("/{membership_id}", response_model=EmployeeResponse)
async def update_employee(
    membership_id: UUID,
    payload: UpdateEmployeeRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> EmployeeResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.MEMBERS_MANAGE)
    await require_membership_scope(session, context, membership_id)
    profile = await session.scalar(
        select(EmployeeProfile)
        .where(
            EmployeeProfile.company_id == context.company_id,
            EmployeeProfile.membership_id == membership_id,
        )
        .with_for_update()
    )
    if profile is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="employee_not_found",
            title="Employee profile not found",
            detail="The employee profile does not exist in the current company.",
        )
    if profile.version != payload.version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Employee profile changed",
            detail="Reload the employee profile before saving again.",
        )
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    department_id = changes.get("department_id")
    if department_id is not None and "department_id" in changes:
        await require_department_scope(session, context, department_id)
        department = await session.scalar(
            select(Department.id).where(
                Department.company_id == context.company_id,
                Department.id == department_id,
                Department.is_active.is_(True),
            )
        )
        if department is None:
            raise ProblemError(
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="department_invalid",
                title="Department is invalid",
                detail="The department must belong to the current company.",
            )
    if "phone" in changes:
        membership = await session.scalar(
            select(CompanyMembership).where(
                CompanyMembership.company_id == context.company_id,
                CompanyMembership.id == membership_id,
            )
        )
        if membership is None:
            raise ProblemError(
                status=404,
                code="employee_not_found",
                title="Employee profile not found",
                detail="The employee profile does not exist in the current company.",
            )
        user = await session.scalar(
            select(User).where(User.id == membership.user_id).with_for_update()
        )
        if user is None:
            raise ProblemError(
                status=404,
                code="employee_not_found",
                title="Employee profile not found",
                detail="The employee profile does not exist in the current company.",
            )
        phone = changes["phone"]
        if isinstance(phone, str):
            await session.execute(
                select(func.pg_advisory_xact_lock(func.hashtextextended(f"phone:{phone}", 0)))
            )
            existing_user = await session.scalar(
                select(User.id).where(User.phone_e164 == phone, User.id != user.id)
            )
            if existing_user is not None:
                raise ProblemError(
                    status=409,
                    code="phone_already_registered",
                    title="Phone already registered",
                    detail="This phone number is already assigned to another account.",
                )
        user.phone_e164 = phone if isinstance(phone, str) else None
        user.phone_verified_at = datetime.now(UTC) if isinstance(phone, str) else None
        user.version += 1
    for field_name, value in changes.items():
        setattr(profile, field_name, value)
    profile.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="employee.profile.updated",
            target_type="employee_profile",
            target_id=profile.id,
            details={"changed_fields": sorted(changes)},
        )
    )
    await session.commit()
    row = (
        await session.execute(
            employee_statement(context.company_id).where(
                EmployeeProfile.membership_id == membership_id
            )
        )
    ).one()
    return employee_response(*row)


@employees_router.post("/{membership_id}/status", response_model=EmployeeResponse)
async def update_employee_status(
    membership_id: UUID,
    payload: UpdateEmployeeStatusRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> EmployeeResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.MEMBERS_MANAGE)
    await require_membership_scope(session, context, membership_id)
    membership = await session.scalar(
        select(CompanyMembership)
        .where(
            CompanyMembership.company_id == context.company_id,
            CompanyMembership.id == membership_id,
        )
        .with_for_update()
    )
    if membership is None:
        raise ProblemError(
            status=404,
            code="employee_not_found",
            title="Employee profile not found",
            detail="The employee profile does not exist in the current company.",
        )
    if membership.id == context.membership.id or membership.role_code == "OWNER":
        raise ProblemError(
            status=409,
            code="protected_membership",
            title="Membership is protected",
            detail="An owner cannot deactivate their own or another owner membership here.",
        )
    if membership.version != payload.version:
        raise ProblemError(
            status=409,
            code="concurrency_conflict",
            title="Membership changed",
            detail="Reload the employee before changing membership status.",
        )
    previous_status = membership.status
    membership.status = payload.status
    membership.version += 1
    now = datetime.now(UTC)
    if payload.status == "inactive":
        refresh_sessions = await session.scalars(
            select(RefreshSession).where(
                RefreshSession.company_id == context.company_id,
                RefreshSession.membership_id == membership.id,
                RefreshSession.revoked_at.is_(None),
            )
        )
        for item in refresh_sessions:
            item.revoked_at = now
        devices = await session.scalars(
            select(Device).where(
                Device.company_id == context.company_id,
                Device.membership_id == membership.id,
                Device.status.in_(("approved", "pending")),
            )
        )
        for device in devices:
            device.status = "revoked"
            device.revoked_at = now
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="employee.membership_status_updated",
            target_type="company_membership",
            target_id=membership.id,
            details={
                "before": previous_status,
                "after": membership.status,
                "reason": payload.reason,
            },
        )
    )
    await session.commit()
    row = (
        await session.execute(
            employee_statement(context.company_id).where(
                EmployeeProfile.membership_id == membership_id
            )
        )
    ).one()
    return employee_response(*row)
