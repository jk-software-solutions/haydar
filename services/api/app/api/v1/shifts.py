from datetime import date, datetime, time
from typing import Annotated, Any, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import Permission, require_permission, tenant_context
from app.core.errors import ProblemError
from app.db.session import get_session
from app.models.devices import AuditLog
from app.models.identity import CompanyMembership
from app.models.organization import Branch, Shift, ShiftAssignment, ShiftException

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


class ShiftFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    start_time: time
    end_time: time
    working_days: list[int] = Field(min_length=1, max_length=7)
    grace_period_minutes: int = Field(default=0, ge=0, le=240)
    break_duration_minutes: int = Field(default=0, ge=0, le=720)
    effective_from: date
    effective_to: date | None = None
    recurrence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("working_days")
    @classmethod
    def validate_working_days(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value) or len(set(value)) != len(value):
            raise ValueError("working_days must contain unique values from 0 through 6")
        return sorted(value)

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from")
        return self


class CreateShiftRequest(ShiftFields):
    pass


class UpdateShiftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    code: str | None = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, min_length=2, max_length=160)
    start_time: time | None = None
    end_time: time | None = None
    working_days: list[int] | None = Field(default=None, min_length=1, max_length=7)
    grace_period_minutes: int | None = Field(default=None, ge=0, le=240)
    break_duration_minutes: int | None = Field(default=None, ge=0, le=720)
    effective_from: date | None = None
    effective_to: date | None = None
    recurrence: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("working_days")
    @classmethod
    def validate_working_days(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and (
            any(day < 0 or day > 6 for day in value) or len(set(value)) != len(value)
        ):
            raise ValueError("working_days must contain unique values from 0 through 6")
        return sorted(value) if value is not None else None

    @model_validator(mode="after")
    def reject_required_nulls(self) -> Self:
        nullable = {"effective_to"}
        for field_name in self.model_fields_set - nullable - {"version"}:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ShiftResponse(BaseModel):
    id: UUID
    code: str
    name: str
    start_time: time
    end_time: time
    is_overnight: bool
    working_days: list[int]
    grace_period_minutes: int
    break_duration_minutes: int
    effective_from: date
    effective_to: date | None
    recurrence: dict[str, Any]
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ShiftListResponse(BaseModel):
    items: list[ShiftResponse]
    page: int
    page_size: int
    total: int


class CreateShiftAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shift_id: UUID
    membership_id: UUID | None = None
    branch_id: UUID | None = None
    effective_from: date
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_target_and_dates(self) -> Self:
        if (self.membership_id is None) == (self.branch_id is None):
            raise ValueError("exactly one membership_id or branch_id is required")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from")
        return self


class ShiftAssignmentResponse(BaseModel):
    id: UUID
    shift_id: UUID
    shift_code: str
    shift_name: str
    membership_id: UUID | None
    branch_id: UUID | None
    effective_from: date
    effective_to: date | None
    created_at: datetime


class CreateShiftExceptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exception_date: date
    is_working_day: bool
    override_start_time: time | None = None
    override_end_time: time | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_override_pair(self) -> Self:
        if (self.override_start_time is None) != (self.override_end_time is None):
            raise ValueError("override start and end times must be supplied together")
        return self


class ShiftExceptionResponse(CreateShiftExceptionRequest):
    id: UUID
    shift_id: UUID
    created_at: datetime


def shift_response(shift: Shift) -> ShiftResponse:
    return ShiftResponse(
        id=shift.id,
        code=shift.code,
        name=shift.name,
        start_time=shift.start_time,
        end_time=shift.end_time,
        is_overnight=shift.is_overnight,
        working_days=shift.working_days,
        grace_period_minutes=shift.grace_period_minutes,
        break_duration_minutes=shift.break_duration_minutes,
        effective_from=shift.effective_from,
        effective_to=shift.effective_to,
        recurrence=shift.recurrence,
        is_active=shift.is_active,
        version=shift.version,
        created_at=shift.created_at,
        updated_at=shift.updated_at,
    )


def assignment_response(assignment: ShiftAssignment, shift: Shift) -> ShiftAssignmentResponse:
    return ShiftAssignmentResponse(
        id=assignment.id,
        shift_id=assignment.shift_id,
        shift_code=shift.code,
        shift_name=shift.name,
        membership_id=assignment.membership_id,
        branch_id=assignment.branch_id,
        effective_from=assignment.effective_from,
        effective_to=assignment.effective_to,
        created_at=assignment.created_at,
    )


async def unique_shift_code(
    session: AsyncSession,
    company_id: UUID,
    code: str,
    excluding_id: UUID | None = None,
) -> None:
    statement = select(Shift.id).where(Shift.company_id == company_id, Shift.code == code)
    if excluding_id is not None:
        statement = statement.where(Shift.id != excluding_id)
    if await session.scalar(statement) is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="shift_code_exists",
            title="Shift code already exists",
            detail="Use a unique shift code within the company.",
        )


@router.post("", response_model=ShiftResponse, status_code=201)
async def create_shift(
    payload: CreateShiftRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> ShiftResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SHIFTS_MANAGE)
    await unique_shift_code(session, context.company_id, payload.code)
    shift = Shift(
        company_id=context.company_id,
        is_overnight=payload.end_time <= payload.start_time,
        **payload.model_dump(),
    )
    session.add(shift)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="shift.created",
            target_type="shift",
            target_id=shift.id,
            details={"code": shift.code, "is_overnight": shift.is_overnight},
        )
    )
    await session.commit()
    await session.refresh(shift)
    return shift_response(shift)


@router.get("", response_model=ShiftListResponse)
async def list_shifts(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    active_only: bool = True,
) -> ShiftListResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SHIFTS_VIEW)
    criteria = [Shift.company_id == context.company_id]
    if active_only:
        criteria.append(Shift.is_active.is_(True))
    total = await session.scalar(select(func.count()).select_from(Shift).where(*criteria))
    shifts = await session.scalars(
        select(Shift)
        .where(*criteria)
        .order_by(Shift.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ShiftListResponse(
        items=[shift_response(shift) for shift in shifts],
        page=page,
        page_size=page_size,
        total=total or 0,
    )


@router.get("/assignments/me", response_model=list[ShiftAssignmentResponse])
async def my_shift_assignments(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> list[ShiftAssignmentResponse]:
    context = tenant_context(auth_session)
    rows = (
        await session.execute(
            select(ShiftAssignment, Shift)
            .join(
                Shift,
                (Shift.company_id == ShiftAssignment.company_id)
                & (Shift.id == ShiftAssignment.shift_id),
            )
            .where(
                ShiftAssignment.company_id == context.company_id,
                ShiftAssignment.membership_id == context.membership.id,
            )
            .order_by(ShiftAssignment.effective_from.desc())
        )
    ).all()
    return [assignment_response(*row) for row in rows]


@router.post("/assignments", response_model=ShiftAssignmentResponse, status_code=201)
async def create_shift_assignment(
    payload: CreateShiftAssignmentRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> ShiftAssignmentResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SHIFTS_MANAGE)
    shift = await session.scalar(
        select(Shift).where(
            Shift.company_id == context.company_id,
            Shift.id == payload.shift_id,
            Shift.is_active.is_(True),
        )
    )
    if shift is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="shift_not_found",
            title="Shift not found",
            detail="The shift does not exist in the current company.",
        )
    if payload.effective_from < shift.effective_from or (
        shift.effective_to is not None
        and (payload.effective_to is None or payload.effective_to > shift.effective_to)
    ):
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="shift_assignment_dates_invalid",
            title="Assignment dates are invalid",
            detail="The assignment must be contained within the shift effective dates.",
        )
    if payload.membership_id is not None:
        target_exists = await session.scalar(
            select(CompanyMembership.id).where(
                CompanyMembership.company_id == context.company_id,
                CompanyMembership.id == payload.membership_id,
                CompanyMembership.status == "active",
            )
        )
        target_column = ShiftAssignment.membership_id
        target_value = payload.membership_id
    else:
        if payload.branch_id is None:
            raise RuntimeError("Validated shift assignment has no target")
        target_exists = await session.scalar(
            select(Branch.id).where(
                Branch.company_id == context.company_id,
                Branch.id == payload.branch_id,
                Branch.is_active.is_(True),
            )
        )
        target_column = ShiftAssignment.branch_id
        target_value = payload.branch_id
    if target_exists is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="shift_assignment_target_not_found",
            title="Assignment target not found",
            detail="The employee or branch does not exist in the current company.",
        )
    overlap = await session.scalar(
        select(ShiftAssignment.id).where(
            ShiftAssignment.company_id == context.company_id,
            target_column == target_value,
            ShiftAssignment.effective_from <= (payload.effective_to or date.max),
            or_(
                ShiftAssignment.effective_to.is_(None),
                ShiftAssignment.effective_to >= payload.effective_from,
            ),
        )
    )
    if overlap is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="shift_assignment_overlap",
            title="Shift assignment overlaps",
            detail="This employee or branch already has a shift in the effective period.",
        )
    assignment = ShiftAssignment(
        company_id=context.company_id,
        shift_id=shift.id,
        membership_id=payload.membership_id,
        branch_id=payload.branch_id,
        assigned_by_membership_id=context.membership.id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    session.add(assignment)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="shift.assignment.created",
            target_type="shift_assignment",
            target_id=assignment.id,
            details={"shift_id": str(shift.id)},
        )
    )
    await session.commit()
    await session.refresh(assignment)
    return assignment_response(assignment, shift)


@router.post("/{shift_id}/exceptions", response_model=ShiftExceptionResponse, status_code=201)
async def create_shift_exception(
    shift_id: UUID,
    payload: CreateShiftExceptionRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> ShiftExceptionResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SHIFTS_MANAGE)
    shift = await session.scalar(
        select(Shift).where(Shift.company_id == context.company_id, Shift.id == shift_id)
    )
    if shift is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="shift_not_found",
            title="Shift not found",
            detail="The shift does not exist in the current company.",
        )
    existing = await session.scalar(
        select(ShiftException.id).where(
            ShiftException.company_id == context.company_id,
            ShiftException.shift_id == shift_id,
            ShiftException.exception_date == payload.exception_date,
        )
    )
    if existing is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="shift_exception_exists",
            title="Shift exception already exists",
            detail="Only one exception can exist for a shift on a date.",
        )
    exception = ShiftException(
        company_id=context.company_id,
        shift_id=shift_id,
        **payload.model_dump(),
    )
    session.add(exception)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="shift.exception.created",
            target_type="shift_exception",
            target_id=exception.id,
            details={"shift_id": str(shift_id), "date": exception.exception_date.isoformat()},
        )
    )
    await session.commit()
    await session.refresh(exception)
    return ShiftExceptionResponse(
        id=exception.id,
        shift_id=exception.shift_id,
        exception_date=exception.exception_date,
        is_working_day=exception.is_working_day,
        override_start_time=exception.override_start_time,
        override_end_time=exception.override_end_time,
        note=exception.note,
        created_at=exception.created_at,
    )


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(
    shift_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> ShiftResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SHIFTS_VIEW)
    shift = await session.scalar(
        select(Shift).where(Shift.company_id == context.company_id, Shift.id == shift_id)
    )
    if shift is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="shift_not_found",
            title="Shift not found",
            detail="The shift does not exist in the current company.",
        )
    return shift_response(shift)


@router.patch("/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: UUID,
    payload: UpdateShiftRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> ShiftResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SHIFTS_MANAGE)
    shift = await session.scalar(
        select(Shift)
        .where(Shift.company_id == context.company_id, Shift.id == shift_id)
        .with_for_update()
    )
    if shift is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="shift_not_found",
            title="Shift not found",
            detail="The shift does not exist in the current company.",
        )
    if shift.version != payload.version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Shift changed",
            detail="Reload the shift before saving again.",
        )
    changes = payload.model_dump(exclude_unset=True, exclude={"version"})
    if "code" in changes:
        await unique_shift_code(session, context.company_id, changes["code"], shift.id)
    effective_from = changes.get("effective_from", shift.effective_from)
    effective_to = changes.get("effective_to", shift.effective_to)
    if effective_to is not None and effective_to < effective_from:
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="shift_dates_invalid",
            title="Shift dates are invalid",
            detail="The effective end cannot precede the start.",
        )
    for field_name, value in changes.items():
        setattr(shift, field_name, value)
    shift.is_overnight = shift.end_time <= shift.start_time
    shift.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="shift.updated",
            target_type="shift",
            target_id=shift.id,
            details={"changed_fields": sorted(changes)},
        )
    )
    await session.commit()
    await session.refresh(shift)
    return shift_response(shift)


@router.delete("/{shift_id}", status_code=204)
async def archive_shift(
    shift_id: UUID,
    version: Annotated[int, Query(ge=1)],
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> None:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SHIFTS_MANAGE)
    shift = await session.scalar(
        select(Shift)
        .where(Shift.company_id == context.company_id, Shift.id == shift_id)
        .with_for_update()
    )
    if shift is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="shift_not_found",
            title="Shift not found",
            detail="The shift does not exist in the current company.",
        )
    if shift.version != version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Shift changed",
            detail="Reload the shift before archiving it.",
        )
    shift.is_active = False
    shift.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="shift.archived",
            target_type="shift",
            target_id=shift.id,
            details={},
        )
    )
    await session.commit()
