from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    membership_scopes,
    require_branch_scope,
    require_department_scope,
    require_membership_scope,
    require_permission,
    require_unrestricted_scope,
    tenant_context,
)
from app.core.errors import ProblemError
from app.core.subscription_catalog import active_subscription, plan_limit
from app.db.session import get_session
from app.models.devices import AuditLog
from app.models.identity import CompanyMembership
from app.models.organization import Branch, Department, EmployeeBranchAssignment, EmployeeProfile

branches_router = APIRouter()
departments_router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


class BranchFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    saudi_short_address: str | None = Field(default=None, max_length=32)
    full_address: str = Field(min_length=3, max_length=1000)
    latitude: Decimal = Field(ge=-90, le=90, decimal_places=6)
    longitude: Decimal = Field(ge=-180, le=180, decimal_places=6)
    geofence_radius_m: int = Field(default=100, ge=20, le=10000)
    timezone: str = Field(default="Asia/Riyadh", min_length=1, max_length=64)
    working_hours: dict[str, Any] = Field(default_factory=dict)
    manager_membership_id: UUID | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", "full_address", "timezone")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("saudi_short_address")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().upper()
        return stripped or None


class CreateBranchRequest(BranchFields):
    pass


class UpdateBranchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    code: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, min_length=2, max_length=160)
    saudi_short_address: str | None = Field(default=None, max_length=32)
    full_address: str | None = Field(default=None, min_length=3, max_length=1000)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, decimal_places=6)
    geofence_radius_m: int | None = Field(default=None, ge=20, le=10000)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    working_hours: dict[str, Any] | None = None
    manager_membership_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name", "full_address", "timezone")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("saudi_short_address")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip().upper()
        return stripped or None

    @model_validator(mode="after")
    def reject_required_nulls(self) -> Self:
        required = {
            "code",
            "name",
            "full_address",
            "latitude",
            "longitude",
            "geofence_radius_m",
            "timezone",
            "working_hours",
            "is_active",
        }
        for field_name in required:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class BranchResponse(BaseModel):
    id: UUID
    code: str
    name: str
    saudi_short_address: str | None
    full_address: str
    latitude: Decimal
    longitude: Decimal
    geofence_radius_m: int
    timezone: str
    working_hours: dict[str, Any]
    manager_membership_id: UUID | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class BranchListResponse(BaseModel):
    items: list[BranchResponse]
    page: int
    page_size: int
    total: int


class DepartmentFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    parent_department_id: UUID | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()


class CreateDepartmentRequest(DepartmentFields):
    pass


class UpdateDepartmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    code: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, min_length=2, max_length=120)
    parent_department_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def reject_required_nulls(self) -> Self:
        for field_name in {"code", "name", "is_active"}:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class DepartmentResponse(BaseModel):
    id: UUID
    code: str
    name: str
    parent_department_id: UUID | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class DepartmentListResponse(BaseModel):
    items: list[DepartmentResponse]
    total: int


class AssignEmployeeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: UUID
    branch_id: UUID
    effective_from: date
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class BranchAssignmentResponse(BaseModel):
    id: UUID
    membership_id: UUID
    branch_id: UUID
    branch_code: str
    branch_name: str
    effective_from: date
    effective_to: date | None
    reason: str
    assigned_by_membership_id: UUID
    created_at: datetime


def branch_response(branch: Branch) -> BranchResponse:
    return BranchResponse(
        id=branch.id,
        code=branch.code,
        name=branch.name,
        saudi_short_address=branch.saudi_short_address,
        full_address=branch.full_address,
        latitude=branch.latitude,
        longitude=branch.longitude,
        geofence_radius_m=branch.geofence_radius_m,
        timezone=branch.timezone,
        working_hours=branch.working_hours,
        manager_membership_id=branch.manager_membership_id,
        is_active=branch.is_active,
        version=branch.version,
        created_at=branch.created_at,
        updated_at=branch.updated_at,
    )


def department_response(department: Department) -> DepartmentResponse:
    return DepartmentResponse(
        id=department.id,
        code=department.code,
        name=department.name,
        parent_department_id=department.parent_department_id,
        is_active=department.is_active,
        version=department.version,
        created_at=department.created_at,
        updated_at=department.updated_at,
    )


def assignment_response(
    assignment: EmployeeBranchAssignment,
    branch: Branch,
) -> BranchAssignmentResponse:
    return BranchAssignmentResponse(
        id=assignment.id,
        membership_id=assignment.membership_id,
        branch_id=assignment.branch_id,
        branch_code=branch.code,
        branch_name=branch.name,
        effective_from=assignment.effective_from,
        effective_to=assignment.effective_to,
        reason=assignment.reason,
        assigned_by_membership_id=assignment.assigned_by_membership_id,
        created_at=assignment.created_at,
    )


async def tenant_membership_exists(
    session: AsyncSession,
    company_id: UUID,
    membership_id: UUID | None,
) -> bool:
    if membership_id is None:
        return True
    return (
        await session.scalar(
            select(CompanyMembership.id).where(
                CompanyMembership.company_id == company_id,
                CompanyMembership.id == membership_id,
                CompanyMembership.status == "active",
            )
        )
        is not None
    )


async def ensure_unique_branch_code(
    session: AsyncSession,
    company_id: UUID,
    code: str,
    excluding_id: UUID | None = None,
) -> None:
    statement = select(Branch.id).where(Branch.company_id == company_id, Branch.code == code)
    if excluding_id is not None:
        statement = statement.where(Branch.id != excluding_id)
    if await session.scalar(statement) is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="branch_code_exists",
            title="Branch code already exists",
            detail="Use a unique branch code within the company.",
        )


async def ensure_unique_department_code(
    session: AsyncSession,
    company_id: UUID,
    code: str,
    excluding_id: UUID | None = None,
) -> None:
    statement = select(Department.id).where(
        Department.company_id == company_id,
        Department.code == code,
    )
    if excluding_id is not None:
        statement = statement.where(Department.id != excluding_id)
    if await session.scalar(statement) is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="department_code_exists",
            title="Department code already exists",
            detail="Use a unique department code within the company.",
        )


@branches_router.post("", response_model=BranchResponse, status_code=201)
async def create_branch(
    payload: CreateBranchRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> BranchResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.BRANCHES_MANAGE)
    await require_unrestricted_scope(session, context)
    subscription = await active_subscription(session, context.company_id)
    branch_limit = plan_limit(subscription[1], "branches") if subscription else 0
    branch_count = int(
        await session.scalar(
            select(func.count())
            .select_from(Branch)
            .where(
                Branch.company_id == context.company_id,
                Branch.is_active.is_(True),
            )
        )
        or 0
    )
    if subscription is None or branch_count >= branch_limit:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="subscription_branch_limit",
            title="Branch limit reached",
            detail="Upgrade or extend the subscription before creating another branch.",
        )
    await ensure_unique_branch_code(session, context.company_id, payload.code)
    if not await tenant_membership_exists(
        session, context.company_id, payload.manager_membership_id
    ):
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="branch_manager_invalid",
            title="Branch manager is invalid",
            detail="The manager must be an active member of the current company.",
        )
    branch = Branch(company_id=context.company_id, **payload.model_dump())
    session.add(branch)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="branch.created",
            target_type="branch",
            target_id=branch.id,
            details={"code": branch.code},
        )
    )
    await session.commit()
    await session.refresh(branch)
    return branch_response(branch)


@branches_router.get("", response_model=BranchListResponse)
async def list_branches(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    active_only: bool = True,
) -> BranchListResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.BRANCHES_VIEW)
    criteria = [Branch.company_id == context.company_id]
    scopes = await membership_scopes(session, context)
    if not scopes.unrestricted:
        own_branch_ids = set(
            await session.scalars(
                select(EmployeeBranchAssignment.branch_id).where(
                    EmployeeBranchAssignment.company_id == context.company_id,
                    EmployeeBranchAssignment.membership_id == context.membership.id,
                    EmployeeBranchAssignment.effective_to.is_(None),
                )
            )
        )
        criteria.append(Branch.id.in_(scopes.branch_ids | own_branch_ids))
    if active_only:
        criteria.append(Branch.is_active.is_(True))
    total = await session.scalar(select(func.count()).select_from(Branch).where(*criteria))
    branches = await session.scalars(
        select(Branch)
        .where(*criteria)
        .order_by(Branch.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return BranchListResponse(
        items=[branch_response(branch) for branch in branches],
        page=page,
        page_size=page_size,
        total=total or 0,
    )


@branches_router.get("/assignments/me", response_model=list[BranchAssignmentResponse])
async def my_branch_assignments(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> list[BranchAssignmentResponse]:
    context = tenant_context(auth_session)
    rows = (
        await session.execute(
            select(EmployeeBranchAssignment, Branch)
            .join(
                Branch,
                (Branch.company_id == EmployeeBranchAssignment.company_id)
                & (Branch.id == EmployeeBranchAssignment.branch_id),
            )
            .where(
                EmployeeBranchAssignment.company_id == context.company_id,
                EmployeeBranchAssignment.membership_id == context.membership.id,
            )
            .order_by(EmployeeBranchAssignment.effective_from.desc())
        )
    ).all()
    return [assignment_response(*row) for row in rows]


@branches_router.get(
    "/assignments/{membership_id}",
    response_model=list[BranchAssignmentResponse],
)
async def employee_branch_assignments(
    membership_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> list[BranchAssignmentResponse]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ASSIGNMENTS_VIEW)
    await require_membership_scope(session, context, membership_id)
    if not await tenant_membership_exists(session, context.company_id, membership_id):
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="employee_not_found",
            title="Employee not found",
            detail="The employee does not exist in the current company.",
        )
    rows = (
        await session.execute(
            select(EmployeeBranchAssignment, Branch)
            .join(
                Branch,
                (Branch.company_id == EmployeeBranchAssignment.company_id)
                & (Branch.id == EmployeeBranchAssignment.branch_id),
            )
            .where(
                EmployeeBranchAssignment.company_id == context.company_id,
                EmployeeBranchAssignment.membership_id == membership_id,
            )
            .order_by(EmployeeBranchAssignment.effective_from.desc())
        )
    ).all()
    return [assignment_response(*row) for row in rows]


@branches_router.post(
    "/assignments",
    response_model=BranchAssignmentResponse,
    status_code=201,
)
async def assign_employee_to_branch(
    payload: AssignEmployeeRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> BranchAssignmentResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ASSIGNMENTS_MANAGE)
    await require_membership_scope(session, context, payload.membership_id)
    await require_branch_scope(session, context, payload.branch_id)
    if not await tenant_membership_exists(session, context.company_id, payload.membership_id):
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="employee_not_found",
            title="Employee not found",
            detail="The employee does not exist in the current company.",
        )
    branch = await session.scalar(
        select(Branch).where(
            Branch.company_id == context.company_id,
            Branch.id == payload.branch_id,
            Branch.is_active.is_(True),
        )
    )
    if branch is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="branch_not_found",
            title="Branch not found",
            detail="The branch does not exist in the current company.",
        )
    current = await session.scalar(
        select(EmployeeBranchAssignment)
        .where(
            EmployeeBranchAssignment.company_id == context.company_id,
            EmployeeBranchAssignment.membership_id == payload.membership_id,
            EmployeeBranchAssignment.effective_to.is_(None),
        )
        .with_for_update()
    )
    if current is not None:
        if current.branch_id == payload.branch_id:
            raise ProblemError(
                status=status.HTTP_409_CONFLICT,
                code="employee_already_assigned",
                title="Employee already assigned",
                detail="The employee is already assigned to this branch.",
            )
        if payload.effective_from <= current.effective_from:
            raise ProblemError(
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="assignment_date_invalid",
                title="Assignment date is invalid",
                detail="A transfer must start after the current assignment began.",
            )
        current.effective_to = payload.effective_from - timedelta(days=1)
        await session.flush()
    assignment = EmployeeBranchAssignment(
        company_id=context.company_id,
        membership_id=payload.membership_id,
        branch_id=payload.branch_id,
        assigned_by_membership_id=context.membership.id,
        effective_from=payload.effective_from,
        reason=payload.reason,
    )
    session.add(assignment)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="employee.branch_assigned" if current is None else "employee.branch_transferred",
            target_type="employee_branch_assignment",
            target_id=assignment.id,
            details={
                "membership_id": str(payload.membership_id),
                "branch_id": str(payload.branch_id),
                "previous_branch_id": str(current.branch_id) if current is not None else None,
            },
        )
    )
    await session.commit()
    await session.refresh(assignment)
    return assignment_response(assignment, branch)


@branches_router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(
    branch_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> BranchResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.BRANCHES_VIEW)
    await require_branch_scope(session, context, branch_id)
    branch = await session.scalar(
        select(Branch).where(Branch.company_id == context.company_id, Branch.id == branch_id)
    )
    if branch is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="branch_not_found",
            title="Branch not found",
            detail="The branch does not exist in the current company.",
        )
    return branch_response(branch)


@branches_router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: UUID,
    payload: UpdateBranchRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> BranchResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.BRANCHES_MANAGE)
    await require_branch_scope(session, context, branch_id)
    branch = await session.scalar(
        select(Branch)
        .where(Branch.company_id == context.company_id, Branch.id == branch_id)
        .with_for_update()
    )
    if branch is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="branch_not_found",
            title="Branch not found",
            detail="The branch does not exist in the current company.",
        )
    if branch.version != payload.version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Branch changed",
            detail="Reload the branch before saving again.",
        )
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    if "code" in changes:
        await ensure_unique_branch_code(session, context.company_id, changes["code"], branch.id)
    if "manager_membership_id" in changes and not await tenant_membership_exists(
        session, context.company_id, changes["manager_membership_id"]
    ):
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="branch_manager_invalid",
            title="Branch manager is invalid",
            detail="The manager must be an active member of the current company.",
        )
    for field_name, value in changes.items():
        setattr(branch, field_name, value)
    branch.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="branch.updated",
            target_type="branch",
            target_id=branch.id,
            details={"changed_fields": sorted(changes)},
        )
    )
    await session.commit()
    await session.refresh(branch)
    return branch_response(branch)


@branches_router.delete("/{branch_id}", status_code=204)
async def archive_branch(
    branch_id: UUID,
    version: Annotated[int, Query(ge=1)],
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> None:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.BRANCHES_MANAGE)
    await require_branch_scope(session, context, branch_id)
    branch = await session.scalar(
        select(Branch)
        .where(Branch.company_id == context.company_id, Branch.id == branch_id)
        .with_for_update()
    )
    if branch is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="branch_not_found",
            title="Branch not found",
            detail="The branch does not exist in the current company.",
        )
    if branch.version != version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Branch changed",
            detail="Reload the branch before archiving it.",
        )
    branch.is_active = False
    branch.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="branch.archived",
            target_type="branch",
            target_id=branch.id,
            details={},
        )
    )
    await session.commit()


@departments_router.post("", response_model=DepartmentResponse, status_code=201)
async def create_department(
    payload: CreateDepartmentRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DepartmentResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_MANAGE)
    await require_unrestricted_scope(session, context)
    await ensure_unique_department_code(session, context.company_id, payload.code)
    if payload.parent_department_id is not None:
        parent = await session.scalar(
            select(Department.id).where(
                Department.company_id == context.company_id,
                Department.id == payload.parent_department_id,
                Department.is_active.is_(True),
            )
        )
        if parent is None:
            raise ProblemError(
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="parent_department_invalid",
                title="Parent department is invalid",
                detail="The parent must belong to the current company.",
            )
    department = Department(company_id=context.company_id, **payload.model_dump())
    session.add(department)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="department.created",
            target_type="department",
            target_id=department.id,
            details={"code": department.code},
        )
    )
    await session.commit()
    await session.refresh(department)
    return department_response(department)


@departments_router.get("", response_model=DepartmentListResponse)
async def list_departments(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    active_only: bool = True,
) -> DepartmentListResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_VIEW)
    criteria = [Department.company_id == context.company_id]
    scopes = await membership_scopes(session, context)
    if not scopes.unrestricted:
        own_department_ids = set(
            await session.scalars(
                select(EmployeeProfile.department_id).where(
                    EmployeeProfile.company_id == context.company_id,
                    EmployeeProfile.membership_id == context.membership.id,
                    EmployeeProfile.department_id.is_not(None),
                )
            )
        )
        criteria.append(Department.id.in_(scopes.department_ids | own_department_ids))
    if active_only:
        criteria.append(Department.is_active.is_(True))
    departments = list(
        await session.scalars(select(Department).where(*criteria).order_by(Department.name.asc()))
    )
    return DepartmentListResponse(
        items=[department_response(item) for item in departments],
        total=len(departments),
    )


@departments_router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DepartmentResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_VIEW)
    await require_department_scope(session, context, department_id)
    department = await session.scalar(
        select(Department).where(
            Department.company_id == context.company_id,
            Department.id == department_id,
        )
    )
    if department is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="department_not_found",
            title="Department not found",
            detail="The department does not exist in the current company.",
        )
    return department_response(department)


@departments_router.patch("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: UUID,
    payload: UpdateDepartmentRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DepartmentResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_MANAGE)
    await require_department_scope(session, context, department_id)
    department = await session.scalar(
        select(Department)
        .where(
            Department.company_id == context.company_id,
            Department.id == department_id,
        )
        .with_for_update()
    )
    if department is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="department_not_found",
            title="Department not found",
            detail="The department does not exist in the current company.",
        )
    if department.version != payload.version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Department changed",
            detail="Reload the department before saving again.",
        )
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    if "code" in changes:
        await ensure_unique_department_code(
            session, context.company_id, changes["code"], department.id
        )
    parent_id = changes.get("parent_department_id")
    if parent_id == department.id:
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="parent_department_invalid",
            title="Parent department is invalid",
            detail="A department cannot be its own parent.",
        )
    if parent_id is not None and "parent_department_id" in changes:
        await require_department_scope(session, context, parent_id)
        parent = await session.scalar(
            select(Department.id).where(
                Department.company_id == context.company_id,
                Department.id == parent_id,
                Department.is_active.is_(True),
            )
        )
        if parent is None:
            raise ProblemError(
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code="parent_department_invalid",
                title="Parent department is invalid",
                detail="The parent must belong to the current company.",
            )
    for field_name, value in changes.items():
        setattr(department, field_name, value)
    department.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="department.updated",
            target_type="department",
            target_id=department.id,
            details={"changed_fields": sorted(changes)},
        )
    )
    await session.commit()
    await session.refresh(department)
    return department_response(department)


@departments_router.delete("/{department_id}", status_code=204)
async def archive_department(
    department_id: UUID,
    version: Annotated[int, Query(ge=1)],
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> None:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_MANAGE)
    await require_department_scope(session, context, department_id)
    department = await session.scalar(
        select(Department)
        .where(
            Department.company_id == context.company_id,
            Department.id == department_id,
        )
        .with_for_update()
    )
    if department is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="department_not_found",
            title="Department not found",
            detail="The department does not exist in the current company.",
        )
    if department.version != version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Department changed",
            detail="Reload the department before archiving it.",
        )
    department.is_active = False
    department.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="department.archived",
            target_type="department",
            target_id=department.id,
            details={},
        )
    )
    await session.commit()
