from datetime import UTC, date, datetime, timedelta
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Response, status
from openpyxl import Workbook
from pydantic import BaseModel, ConfigDict, Field
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    membership_scopes,
    require_branch_scope,
    require_department_scope,
    require_group_scope,
    require_membership_scope,
    require_permission,
    tenant_context,
    visible_membership_ids,
)
from app.core.errors import ProblemError
from app.core.subscription_catalog import active_subscription
from app.db.session import get_session
from app.models.attendance import AttendanceRecord, GeofenceExitEvent, PermissionRequest
from app.models.files import StoredFile
from app.models.organization import (
    Branch,
    EmployeeBranchAssignment,
    EmployeeGroupMembership,
    EmployeeProfile,
    Shift,
)
from app.models.platform import AttendanceLeaderboardSetting, ExportJob
from app.models.workforce import (
    EmployeeDocument,
    LeaveRequest,
    TaskAssignee,
    TaskStatusHistory,
    WorkTask,
)
from app.services.idempotency import IdempotencyKey, begin_idempotency, complete_idempotency

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]

try:
    import arabic_reshaper
    from bidi.algorithm import get_display as bidi_display
except ImportError:  # Optional until the API environment installs Arabic PDF support.
    arabic_reshaper = None
    bidi_display = None


class AttendanceReportItem(BaseModel):
    membership_id: UUID
    branch_id: UUID
    shift_id: UUID
    work_date: date
    status: str
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    late_minutes: int
    early_departure_minutes: int
    worked_minutes: int
    is_manual: bool


class AttendanceReportResponse(BaseModel):
    items: list[AttendanceReportItem]
    total: int
    status_counts: dict[str, int]
    total_worked_minutes: int
    total_late_minutes: int
    total_early_departure_minutes: int


class OverviewReportResponse(BaseModel):
    employees: int
    branches: int
    shifts: int
    attendance_records: int
    pending_leave_requests: int
    pending_permission_requests: int
    open_tasks: int
    expired_documents: int
    expiring_documents: int
    unauthorized_geofence_exits: int


class GeofenceExitReportResponse(BaseModel):
    items: list[dict[str, object]]
    total: int
    status_counts: dict[str, int]


class DatasetReportResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    status_counts: dict[str, int]


class ExportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_type: Literal[
        "attendance",
        "geofence_exits",
        "leave",
        "permissions",
        "tasks",
        "documents",
        "branches",
        "shifts",
    ]
    report_types: list[Literal[
        "attendance",
        "geofence_exits",
        "leave",
        "permissions",
        "tasks",
        "documents",
        "branches",
        "shifts",
    ]] = Field(default_factory=list, max_length=8)
    export_format: Literal["pdf", "xlsx"]
    date_from: date | None = None
    date_to: date | None = None
    membership_id: UUID | None = None
    branch_id: UUID | None = None
    department_id: UUID | None = None
    group_id: UUID | None = None
    shift_id: UUID | None = None
    status: str | None = Field(default=None, max_length=40)
    locale: Literal["ar", "en"] = "ar"


class ExportJobResponse(BaseModel):
    id: UUID
    report_type: str
    export_format: str
    status: str
    progress_percent: int
    filename: str | None
    error_message: str | None
    completed_at: datetime | None
    expires_at: datetime
    created_at: datetime
    filters: dict[str, object] = Field(default_factory=dict)


class LeaderboardSettingRequest(BaseModel):
    visibility: Literal["manager_only", "branch", "company", "disabled"]
    enabled: bool
    anonymize: bool = False


class LeaderboardItem(BaseModel):
    rank: int
    display_name: str
    on_time_days: int
    worked_minutes: int


@router.put("/leaderboard/settings")
async def update_leaderboard_settings(
    payload: LeaderboardSettingRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> dict[str, object]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    if context.membership.role_code not in {"OWNER", "MANAGER", "HR_OFFICER"}:
        raise ProblemError(
            status=403,
            code="permission_denied",
            title="Permission denied",
            detail="Only company administrators can configure attendance ranking privacy.",
        )
    item = await session.get(AttendanceLeaderboardSetting, context.company_id)
    if item is None:
        item = AttendanceLeaderboardSetting(company_id=context.company_id)
        session.add(item)
    item.visibility = payload.visibility
    item.enabled = payload.enabled and payload.visibility != "disabled"
    item.anonymize = payload.anonymize
    await session.commit()
    return {
        "visibility": item.visibility,
        "enabled": item.enabled,
        "anonymize": item.anonymize,
    }


@router.get("/leaderboard/settings")
async def get_leaderboard_settings(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> dict[str, object]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    item = await session.get(AttendanceLeaderboardSetting, context.company_id)
    if item is None:
        return {"visibility": "disabled", "enabled": False, "anonymize": False}
    return {
        "visibility": item.visibility,
        "enabled": item.enabled,
        "anonymize": item.anonymize,
    }


@router.get("/leaderboard", response_model=list[LeaderboardItem])
async def attendance_leaderboard(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
) -> list[LeaderboardItem]:
    context = tenant_context(auth_session)
    setting = await session.get(AttendanceLeaderboardSetting, context.company_id)
    if setting is None or not setting.enabled or setting.visibility == "disabled":
        return []
    manager = context.membership.role_code in {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    if setting.visibility == "manager_only" and not manager:
        return []
    if branch_id is not None:
        await require_branch_scope(session, context, branch_id)
    if department_id is not None:
        await require_department_scope(session, context, department_id)
    period_end = date_to or date.today()
    period_start = date_from or period_end - timedelta(days=30)
    if period_start > period_end or (period_end - period_start).days > 366:
        raise ProblemError(
            status=422,
            code="report_period_invalid",
            title="Report period is invalid",
            detail="Choose a period of no more than 366 days with the start before the end.",
        )
    criteria: list[Any] = [
        AttendanceRecord.company_id == context.company_id,
        AttendanceRecord.status.in_(("on_time", "late", "on_permission")),
        AttendanceRecord.work_date >= period_start,
        AttendanceRecord.work_date <= period_end,
    ]
    visible = await visible_membership_ids(session, context)
    if visible is not None:
        criteria.append(AttendanceRecord.membership_id.in_(visible))
    if setting.visibility == "branch" and not manager:
        branch_id = await session.scalar(
            select(EmployeeBranchAssignment.branch_id).where(
                EmployeeBranchAssignment.company_id == context.company_id,
                EmployeeBranchAssignment.membership_id == context.membership.id,
                EmployeeBranchAssignment.effective_to.is_(None),
            )
        )
        if branch_id is None:
            return []
        criteria.append(AttendanceRecord.branch_id == branch_id)
    if branch_id is not None:
        criteria.append(AttendanceRecord.branch_id == branch_id)
    if department_id is not None:
        criteria.append(EmployeeProfile.department_id == department_id)
    rows = (
        await session.execute(
            select(
                EmployeeProfile.display_name,
                func.count(AttendanceRecord.id).filter(AttendanceRecord.late_minutes == 0),
                func.coalesce(func.sum(AttendanceRecord.worked_minutes), 0),
            )
            .join(
                EmployeeProfile,
                (EmployeeProfile.company_id == AttendanceRecord.company_id)
                & (EmployeeProfile.membership_id == AttendanceRecord.membership_id),
            )
            .where(*criteria)
            .group_by(EmployeeProfile.display_name, AttendanceRecord.membership_id)
            .order_by(
                func.count(AttendanceRecord.id).filter(AttendanceRecord.late_minutes == 0).desc(),
                func.sum(AttendanceRecord.worked_minutes).desc(),
            )
            .limit(20)
        )
    ).all()
    return [
        LeaderboardItem(
            rank=index,
            display_name=f"Employee {index}" if setting.anonymize else row[0],
            on_time_days=int(row[1]),
            worked_minutes=int(row[2]),
        )
        for index, row in enumerate(rows, start=1)
    ]


def export_response(job: ExportJob) -> ExportJobResponse:
    return ExportJobResponse.model_validate(job, from_attributes=True)


async def expire_export_jobs(
    session: AsyncSession,
    company_id: UUID,
    *,
    requested_by_membership_id: UUID | None = None,
) -> int:
    criteria: list[Any] = [
        ExportJob.company_id == company_id,
        ExportJob.expires_at <= datetime.now(UTC),
        ExportJob.status != "expired",
    ]
    if requested_by_membership_id is not None:
        criteria.append(ExportJob.requested_by_membership_id == requested_by_membership_id)
    jobs = list(
        await session.scalars(select(ExportJob).where(*criteria).with_for_update())
    )
    for job in jobs:
        job.status = "expired"
        job.file_content = None
        job.content_type = None
        job.progress_percent = 100
    return len(jobs)


def attendance_criteria(
    company_id: UUID,
    date_from: date | None,
    date_to: date | None,
    membership_id: UUID | None,
    branch_id: UUID | None,
    record_status: str | None,
    shift_id: UUID | None = None,
    department_id: UUID | None = None,
) -> list[Any]:
    criteria: list[Any] = [AttendanceRecord.company_id == company_id]
    if date_from:
        criteria.append(AttendanceRecord.work_date >= date_from)
    if date_to:
        criteria.append(AttendanceRecord.work_date <= date_to)
    if membership_id:
        criteria.append(AttendanceRecord.membership_id == membership_id)
    if branch_id:
        criteria.append(AttendanceRecord.branch_id == branch_id)
    if record_status:
        criteria.append(AttendanceRecord.status == record_status)
    if shift_id:
        criteria.append(AttendanceRecord.shift_id == shift_id)
    if department_id:
        criteria.append(
            AttendanceRecord.membership_id.in_(
                select(EmployeeProfile.membership_id).where(
                    EmployeeProfile.company_id == company_id,
                    EmployeeProfile.department_id == department_id,
                )
            )
        )
    return criteria


@router.get("/attendance", response_model=AttendanceReportResponse)
async def attendance_report(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
    membership_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
    group_id: UUID | None = None,
    shift_id: UUID | None = None,
    record_status: Annotated[str | None, Query(alias="status")] = None,
) -> AttendanceReportResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    if membership_id is not None:
        await require_membership_scope(session, context, membership_id)
    if branch_id is not None:
        await require_branch_scope(session, context, branch_id)
    if department_id is not None:
        await require_department_scope(session, context, department_id)
    if group_id is not None:
        await require_group_scope(session, context, group_id)
    criteria = attendance_criteria(
        context.company_id,
        date_from,
        date_to,
        membership_id,
        branch_id,
        record_status,
        shift_id,
        department_id,
    )
    visible = await visible_membership_ids(session, context)
    if visible is not None:
        criteria.append(AttendanceRecord.membership_id.in_(visible))
    if group_id is not None:
        criteria.append(
            AttendanceRecord.membership_id.in_(
                select(EmployeeGroupMembership.membership_id).where(
                    EmployeeGroupMembership.company_id == context.company_id,
                    EmployeeGroupMembership.group_id == group_id,
                )
            )
        )
    records = list(
        await session.scalars(
            select(AttendanceRecord)
            .where(*criteria)
            .order_by(AttendanceRecord.work_date.desc())
            .limit(5000)
        )
    )
    counts: dict[str, int] = {}
    for record in records:
        counts[record.status] = counts.get(record.status, 0) + 1
    return AttendanceReportResponse(
        items=[AttendanceReportItem.model_validate(item, from_attributes=True) for item in records],
        total=len(records),
        status_counts=counts,
        total_worked_minutes=sum(item.worked_minutes for item in records),
        total_late_minutes=sum(item.late_minutes for item in records),
        total_early_departure_minutes=sum(item.early_departure_minutes for item in records),
    )


@router.get("/geofence-exits", response_model=GeofenceExitReportResponse)
async def geofence_exit_report(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
    membership_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
    group_id: UUID | None = None,
    shift_id: UUID | None = None,
    event_status: Annotated[str | None, Query(alias="status")] = None,
) -> GeofenceExitReportResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    if membership_id is not None:
        await require_membership_scope(session, context, membership_id)
    if branch_id is not None:
        await require_branch_scope(session, context, branch_id)
    if department_id is not None:
        await require_department_scope(session, context, department_id)
    if group_id is not None:
        await require_group_scope(session, context, group_id)
    criteria: list[Any] = [GeofenceExitEvent.company_id == context.company_id]
    visible = await visible_membership_ids(session, context)
    if visible is not None:
        criteria.append(GeofenceExitEvent.membership_id.in_(visible))
    if membership_id:
        criteria.append(GeofenceExitEvent.membership_id == membership_id)
    if branch_id:
        criteria.append(GeofenceExitEvent.branch_id == branch_id)
    if department_id:
        criteria.append(
            GeofenceExitEvent.membership_id.in_(
                select(EmployeeProfile.membership_id).where(
                    EmployeeProfile.company_id == context.company_id,
                    EmployeeProfile.department_id == department_id,
                )
            )
        )
    if group_id:
        criteria.append(
            GeofenceExitEvent.membership_id.in_(
                select(EmployeeGroupMembership.membership_id).where(
                    EmployeeGroupMembership.company_id == context.company_id,
                    EmployeeGroupMembership.group_id == group_id,
                )
            )
        )
    if shift_id:
        criteria.append(GeofenceExitEvent.shift_id == shift_id)
    if event_status:
        criteria.append(GeofenceExitEvent.status == event_status)
    if date_from:
        criteria.append(
            GeofenceExitEvent.detected_at >= datetime.combine(date_from, datetime.min.time(), UTC)
        )
    if date_to:
        criteria.append(
            GeofenceExitEvent.detected_at
            < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), UTC)
        )
    events = list(
        await session.scalars(
            select(GeofenceExitEvent)
            .where(*criteria)
            .order_by(GeofenceExitEvent.detected_at.desc())
            .limit(5000)
        )
    )
    counts: dict[str, int] = {}
    items: list[dict[str, object]] = []
    for event in events:
        counts[event.status] = counts.get(event.status, 0) + 1
        items.append(
            {
                "id": str(event.id),
                "membership_id": str(event.membership_id),
                "branch_id": str(event.branch_id),
                "shift_id": str(event.shift_id),
                "status": event.status,
                "detected_at": event.detected_at.isoformat(),
                "distance_m": event.distance_m or 0,
                "accuracy_m": event.accuracy_m or 0,
                "review_comment": event.review_comment or "",
            }
        )
    return GeofenceExitReportResponse(items=items, total=len(items), status_counts=counts)


@router.get("/overview", response_model=OverviewReportResponse)
async def overview_report(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> OverviewReportResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    today = date.today()
    visible = await visible_membership_ids(session, context)
    scopes = await membership_scopes(session, context)
    employee_scope = [] if visible is None else [EmployeeProfile.membership_id.in_(visible)]
    attendance_scope = [] if visible is None else [AttendanceRecord.membership_id.in_(visible)]
    request_scope = [] if visible is None else [LeaveRequest.membership_id.in_(visible)]
    permission_scope = [] if visible is None else [PermissionRequest.membership_id.in_(visible)]
    document_scope = [] if visible is None else [EmployeeDocument.membership_id.in_(visible)]
    branch_scope = [] if scopes.unrestricted else [Branch.id.in_(scopes.branch_ids)]
    task_scope = (
        []
        if visible is None
        else [
            WorkTask.id.in_(
                select(TaskAssignee.task_id).where(TaskAssignee.membership_id.in_(visible))
            )
        ]
    )
    return OverviewReportResponse(
        employees=int(
            await session.scalar(
                select(func.count())
                .select_from(EmployeeProfile)
                .where(EmployeeProfile.company_id == context.company_id, *employee_scope)
            )
            or 0
        ),
        branches=int(
            await session.scalar(
                select(func.count())
                .select_from(Branch)
                .where(
                    Branch.company_id == context.company_id,
                    Branch.is_active.is_(True),
                    *branch_scope,
                )
            )
            or 0
        ),
        shifts=int(
            await session.scalar(
                select(func.count())
                .select_from(Shift)
                .where(Shift.company_id == context.company_id, Shift.is_active.is_(True))
            )
            or 0
        ),
        attendance_records=int(
            await session.scalar(
                select(func.count())
                .select_from(AttendanceRecord)
                .where(AttendanceRecord.company_id == context.company_id, *attendance_scope)
            )
            or 0
        ),
        pending_leave_requests=int(
            await session.scalar(
                select(func.count())
                .select_from(LeaveRequest)
                .where(
                    LeaveRequest.company_id == context.company_id,
                    LeaveRequest.status == "pending",
                    *request_scope,
                )
            )
            or 0
        ),
        pending_permission_requests=int(
            await session.scalar(
                select(func.count())
                .select_from(PermissionRequest)
                .where(
                    PermissionRequest.company_id == context.company_id,
                    PermissionRequest.status == "pending",
                    *permission_scope,
                )
            )
            or 0
        ),
        open_tasks=int(
            await session.scalar(
                select(func.count())
                .select_from(WorkTask)
                .where(
                    WorkTask.company_id == context.company_id,
                    WorkTask.status.not_in(("completed", "postponed")),
                    *task_scope,
                )
            )
            or 0
        ),
        expired_documents=int(
            await session.scalar(
                select(func.count())
                .select_from(EmployeeDocument)
                .where(
                    EmployeeDocument.company_id == context.company_id,
                    EmployeeDocument.expires_on < today,
                    *document_scope,
                )
            )
            or 0
        ),
        expiring_documents=int(
            await session.scalar(
                select(func.count())
                .select_from(EmployeeDocument)
                .where(
                    EmployeeDocument.company_id == context.company_id,
                    EmployeeDocument.expires_on >= today,
                    EmployeeDocument.expires_on <= today + timedelta(days=30),
                    *document_scope,
                )
            )
            or 0
        ),
        unauthorized_geofence_exits=int(
            await session.scalar(
                select(func.count())
                .select_from(GeofenceExitEvent)
                .where(
                    GeofenceExitEvent.company_id == context.company_id,
                    GeofenceExitEvent.status.in_(("unauthorized", "confirmed_unauthorized")),
                    *([] if visible is None else [GeofenceExitEvent.membership_id.in_(visible)]),
                )
            )
            or 0
        ),
    )


async def report_membership_scope(
    session: AsyncSession,
    context: Any,
    *,
    membership_id: UUID | None,
    branch_id: UUID | None,
    department_id: UUID | None,
    group_id: UUID | None,
) -> frozenset[UUID] | None:
    if membership_id is not None:
        await require_membership_scope(session, context, membership_id)
    if branch_id is not None:
        await require_branch_scope(session, context, branch_id)
    if department_id is not None:
        await require_department_scope(session, context, department_id)
    if group_id is not None:
        await require_group_scope(session, context, group_id)
    visible = await visible_membership_ids(session, context)
    filters: list[set[UUID]] = []
    if visible is not None:
        filters.append(set(visible))
    if membership_id is not None:
        filters.append({membership_id})
    if branch_id is not None:
        filters.append(
            set(
                await session.scalars(
                    select(EmployeeBranchAssignment.membership_id).where(
                        EmployeeBranchAssignment.company_id == context.company_id,
                        EmployeeBranchAssignment.branch_id == branch_id,
                        EmployeeBranchAssignment.effective_to.is_(None),
                    )
                )
            )
        )
    if department_id is not None:
        filters.append(
            set(
                await session.scalars(
                    select(EmployeeProfile.membership_id).where(
                        EmployeeProfile.company_id == context.company_id,
                        EmployeeProfile.department_id == department_id,
                    )
                )
            )
        )
    if group_id is not None:
        filters.append(
            set(
                await session.scalars(
                    select(EmployeeGroupMembership.membership_id).where(
                        EmployeeGroupMembership.company_id == context.company_id,
                        EmployeeGroupMembership.group_id == group_id,
                    )
                )
            )
        )
    if not filters:
        return None
    result = filters[0]
    for values in filters[1:]:
        result &= values
    return frozenset(result)


def dataset_response(items: list[dict[str, Any]]) -> DatasetReportResponse:
    counts: dict[str, int] = {}
    for item in items:
        item_status = str(item.get("status") or "unknown")
        counts[item_status] = counts.get(item_status, 0) + 1
    return DatasetReportResponse(items=items, total=len(items), status_counts=counts)


@router.get("/leave", response_model=DatasetReportResponse)
async def leave_report(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
    membership_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
    group_id: UUID | None = None,
    report_status: Annotated[str | None, Query(alias="status")] = None,
) -> DatasetReportResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    members = await report_membership_scope(
        session,
        context,
        membership_id=membership_id,
        branch_id=branch_id,
        department_id=department_id,
        group_id=group_id,
    )
    criteria: list[Any] = [LeaveRequest.company_id == context.company_id]
    if members is not None:
        criteria.append(LeaveRequest.membership_id.in_(members))
    if date_from:
        criteria.append(LeaveRequest.ends_on >= date_from)
    if date_to:
        criteria.append(LeaveRequest.starts_on <= date_to)
    if report_status:
        criteria.append(LeaveRequest.status == report_status)
    rows = await session.scalars(
        select(LeaveRequest).where(*criteria).order_by(LeaveRequest.created_at.desc()).limit(5000)
    )
    return dataset_response(
        [
            {
                "id": str(item.id),
                "membership_id": str(item.membership_id),
                "starts_on": item.starts_on,
                "ends_on": item.ends_on,
                "days": item.days,
                "status": item.status,
                "reason": item.reason,
            }
            for item in rows
        ]
    )


@router.get("/permissions", response_model=DatasetReportResponse)
async def permission_report(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
    membership_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
    group_id: UUID | None = None,
    report_status: Annotated[str | None, Query(alias="status")] = None,
) -> DatasetReportResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    members = await report_membership_scope(
        session,
        context,
        membership_id=membership_id,
        branch_id=branch_id,
        department_id=department_id,
        group_id=group_id,
    )
    criteria: list[Any] = [PermissionRequest.company_id == context.company_id]
    if members is not None:
        criteria.append(PermissionRequest.membership_id.in_(members))
    if date_from:
        criteria.append(
            PermissionRequest.ends_at
            >= datetime.combine(date_from, datetime.min.time(), UTC)
        )
    if date_to:
        criteria.append(
            PermissionRequest.starts_at
            < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), UTC)
        )
    if report_status:
        criteria.append(PermissionRequest.status == report_status)
    rows = await session.scalars(
        select(PermissionRequest)
        .where(*criteria)
        .order_by(PermissionRequest.created_at.desc())
        .limit(5000)
    )
    return dataset_response(
        [
            {
                "id": str(item.id),
                "membership_id": str(item.membership_id),
                "request_type": item.request_type,
                "starts_at": item.starts_at,
                "ends_at": item.ends_at,
                "status": item.status,
                "reason": item.reason,
            }
            for item in rows
        ]
    )


@router.get("/tasks", response_model=DatasetReportResponse)
async def task_report(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
    membership_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
    group_id: UUID | None = None,
    report_status: Annotated[str | None, Query(alias="status")] = None,
) -> DatasetReportResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    members = await report_membership_scope(
        session,
        context,
        membership_id=membership_id,
        branch_id=branch_id,
        department_id=department_id,
        group_id=group_id,
    )
    criteria: list[Any] = [WorkTask.company_id == context.company_id]
    if members is not None:
        criteria.append(
            WorkTask.id.in_(
                select(TaskAssignee.task_id).where(TaskAssignee.membership_id.in_(members))
            )
        )
    if date_from:
        criteria.append(
            WorkTask.created_at >= datetime.combine(date_from, datetime.min.time(), UTC)
        )
    if date_to:
        criteria.append(
            WorkTask.created_at
            < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), UTC)
        )
    if report_status:
        criteria.append(WorkTask.status == report_status)
    tasks = list(
        await session.scalars(
            select(WorkTask).where(*criteria).order_by(WorkTask.created_at.desc()).limit(5000)
        )
    )
    assignees: dict[UUID, list[str]] = {item.id: [] for item in tasks}
    if assignees:
        for task_id, assignee_id in await session.execute(
            select(TaskAssignee.task_id, TaskAssignee.membership_id).where(
                TaskAssignee.task_id.in_(assignees)
            )
        ):
            assignees[task_id].append(str(assignee_id))
    return dataset_response(
        [
            {
                "id": str(item.id),
                "title": item.title,
                "priority": item.priority,
                "due_at": item.due_at,
                "status": item.status,
                "created_at": item.created_at,
                "assignee_ids": assignees[item.id],
            }
            for item in tasks
        ]
    )


@router.get("/documents", response_model=DatasetReportResponse)
async def document_report(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
    membership_id: UUID | None = None,
    branch_id: UUID | None = None,
    department_id: UUID | None = None,
    group_id: UUID | None = None,
    report_status: Annotated[str | None, Query(alias="status")] = None,
) -> DatasetReportResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    members = await report_membership_scope(
        session,
        context,
        membership_id=membership_id,
        branch_id=branch_id,
        department_id=department_id,
        group_id=group_id,
    )
    criteria: list[Any] = [EmployeeDocument.company_id == context.company_id]
    if members is not None:
        criteria.append(EmployeeDocument.membership_id.in_(members))
    if date_from:
        criteria.append(EmployeeDocument.expires_on >= date_from)
    if date_to:
        criteria.append(EmployeeDocument.expires_on <= date_to)
    if report_status:
        criteria.append(EmployeeDocument.review_status == report_status)
    rows = await session.scalars(
        select(EmployeeDocument)
        .where(*criteria)
        .order_by(EmployeeDocument.expires_on.asc().nullslast())
        .limit(5000)
    )
    return dataset_response(
        [
            {
                "id": str(item.id),
                "membership_id": str(item.membership_id),
                "document_type": item.document_type,
                "document_number": item.document_number,
                "issued_on": item.issued_on,
                "expires_on": item.expires_on,
                "status": item.review_status,
            }
            for item in rows
        ]
    )


ReportDisplayMaps = tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]

REPORT_TITLES = {
    "ar": {
        "attendance": "تقرير الحضور والانصراف",
        "geofence_exits": "تقرير مغادرة نطاق الفرع",
        "leave": "تقرير الإجازات",
        "permissions": "تقرير الاستئذانات",
        "tasks": "تقرير المهام",
        "documents": "تقرير وثائق الموظفين",
        "branches": "تقرير الفروع",
        "shifts": "تقرير الورديات",
    },
    "en": {
        "attendance": "Attendance and Check-out Report",
        "geofence_exits": "Branch Geofence Exit Report",
        "leave": "Leave Report",
        "permissions": "Permission Requests Report",
        "tasks": "Work Tasks Report",
        "documents": "Employee Documents Report",
        "branches": "Branches Report",
        "shifts": "Shifts Report",
    },
}

REPORT_HEADERS = {
    "ar": {
        "attendance": ["التاريخ", "الموظف", "الفرع", "الوردية", "الحالة", "الحضور", "الانصراف", "ساعات العمل", "التأخير", "الانصراف المبكر"],
        "geofence_exits": ["وقت الرصد", "الموظف", "الفرع", "الوردية", "الحالة", "المسافة", "دقة الموقع", "ملاحظة المراجعة"],
        "leave": ["الموظف", "من تاريخ", "إلى تاريخ", "عدد الأيام", "الحالة", "السبب"],
        "permissions": ["الموظف", "نوع الاستئذان", "من وقت", "إلى وقت", "الحالة", "السبب"],
        "tasks": ["المهمة", "تاريخ الإنشاء", "تاريخ الإنجاز", "موعد التسليم", "الأولوية", "الحالة", "أنشأها"],
        "documents": ["الموظف", "نوع الوثيقة", "رقم الوثيقة", "تاريخ الإصدار", "تاريخ الانتهاء", "حالة المراجعة"],
        "branches": ["رمز الفرع", "اسم الفرع", "العنوان", "المنطقة الزمنية", "نطاق الحضور", "الحالة"],
        "shifts": ["رمز الوردية", "اسم الوردية", "بداية الوردية", "نهاية الوردية", "وردية ليلية", "السماح بالدقائق", "الحالة"],
    },
    "en": {
        "attendance": ["Date", "Employee", "Branch", "Shift", "Status", "Check in", "Check out", "Worked time", "Late", "Early departure"],
        "geofence_exits": ["Detected at", "Employee", "Branch", "Shift", "Status", "Distance", "Location accuracy", "Review note"],
        "leave": ["Employee", "From date", "To date", "Days", "Status", "Reason"],
        "permissions": ["Employee", "Permission type", "From time", "To time", "Status", "Reason"],
        "tasks": ["Task", "Created at", "Completed at", "Due date", "Priority", "Status", "Created by"],
        "documents": ["Employee", "Document type", "Document number", "Issued on", "Expires on", "Review status"],
        "branches": ["Branch code", "Branch name", "Address", "Timezone", "Attendance radius", "Status"],
        "shifts": ["Shift code", "Shift name", "Start time", "End time", "Overnight", "Grace period", "Status"],
    },
}

STATUS_LABELS = {
    "ar": {
        "on_time": "حاضر في الوقت",
        "late": "متأخر",
        "on_permission": "استئذان معتمد",
        "permission_return_late": "عودة متأخرة من الاستئذان",
        "early_departure_unauthorized": "انصراف مبكر بدون إذن",
        "unauthorized": "غير مصرح به",
        "confirmed_unauthorized": "مغادرة غير مصرح بها مؤكدة",
        "missing_check_out": "لم يسجل الانصراف",
        "manual_attendance": "تسجيل يدوي",
        "absent": "غائب",
        "on_leave": "في إجازة",
        "pending": "قيد الانتظار",
        "approved": "معتمد",
        "rejected": "مرفوض",
        "new": "جديدة",
        "viewed": "تمت المشاهدة",
        "in_progress": "قيد التنفيذ",
        "completed": "مكتملة",
        "blocked": "متوقفة",
        "postponed": "مؤجلة",
        "needs_more_time": "تحتاج وقتاً إضافياً",
        "active": "نشط",
        "inactive": "غير نشط",
        "pending_review": "بانتظار المراجعة",
        "accepted": "مقبول",
        "expired": "منتهي",
        "export_expired": "انتهت صلاحية الملف",
    },
    "en": {
        "on_time": "On time",
        "late": "Late",
        "on_permission": "Approved permission",
        "permission_return_late": "Late permission return",
        "early_departure_unauthorized": "Unauthorized early departure",
        "unauthorized": "Unauthorized",
        "confirmed_unauthorized": "Confirmed unauthorized exit",
        "missing_check_out": "Missing check-out",
        "manual_attendance": "Manual entry",
        "absent": "Absent",
        "on_leave": "On leave",
        "pending": "Pending",
        "approved": "Approved",
        "rejected": "Rejected",
        "new": "New",
        "viewed": "Viewed",
        "in_progress": "In progress",
        "completed": "Completed",
        "blocked": "Blocked",
        "postponed": "Postponed",
        "needs_more_time": "Needs more time",
        "active": "Active",
        "inactive": "Inactive",
        "pending_review": "Pending review",
        "accepted": "Accepted",
        "expired": "Expired",
        "export_expired": "Export expired",
    },
}

VALUE_LABELS = {
    "ar": {
        "low": "منخفضة",
        "normal": "عادية",
        "high": "عالية",
        "urgent": "عاجلة",
        "one_hour": "ساعة واحدة",
        "multiple_hours": "فترة محددة",
        "until_shift_end": "حتى نهاية الوردية",
        "custom": "مخصص",
        "residency": "إقامة",
        "passport": "جواز سفر",
        "medical_insurance": "تأمين طبي",
        "employment_contract": "عقد عمل",
        "driving_license": "رخصة قيادة",
        "vehicle_insurance": "تأمين مركبة",
        "yes": "نعم",
        "no": "لا",
    },
    "en": {
        "low": "Low",
        "normal": "Normal",
        "high": "High",
        "urgent": "Urgent",
        "one_hour": "One hour",
        "multiple_hours": "Specific period",
        "until_shift_end": "Until shift end",
        "custom": "Custom",
        "residency": "Residency",
        "passport": "Passport",
        "medical_insurance": "Medical insurance",
        "employment_contract": "Employment contract",
        "driving_license": "Driving license",
        "vehicle_insurance": "Vehicle insurance",
        "yes": "Yes",
        "no": "No",
    },
}


async def report_display_maps(session: AsyncSession, company_id: UUID) -> ReportDisplayMaps:
    employees = await session.scalars(
        select(EmployeeProfile).where(EmployeeProfile.company_id == company_id)
    )
    branches = await session.scalars(select(Branch).where(Branch.company_id == company_id))
    shifts = await session.scalars(select(Shift).where(Shift.company_id == company_id))
    employee_names = {str(item.membership_id): item.display_name for item in employees}
    branch_names = {str(item.id): item.name for item in branches}
    branch_timezones = {str(item.id): item.timezone for item in branches}
    shift_names = {str(item.id): item.name for item in shifts}
    return employee_names, branch_names, branch_timezones, shift_names


def value_label(value: object, locale: str) -> str:
    text = str(value)
    return STATUS_LABELS.get(locale, STATUS_LABELS["en"]).get(
        text,
        VALUE_LABELS.get(locale, VALUE_LABELS["en"]).get(text, text),
    )


def mapped_name(value: object, mapping: dict[str, str], fallback: str) -> str:
    text = mapping.get(str(value))
    return text or fallback


def format_report_datetime(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return "—"
    try:
        local_value = value.astimezone(ZoneInfo(timezone_name))
    except (ValueError, TypeError):
        local_value = value
    return local_value.strftime("%Y-%m-%d %H:%M")


def format_report_date(value: date | None) -> str:
    return value.isoformat() if value is not None else "—"


async def export_rows(
    session: AsyncSession,
    company_id: UUID,
    payload: ExportCreateRequest,
    visible_members: frozenset[UUID] | None,
    visible_branches: frozenset[UUID] | None,
    display_maps: ReportDisplayMaps,
) -> tuple[list[str], list[list[object]]]:
    locale = payload.locale
    employee_names, branch_names, branch_timezones, shift_names = display_maps

    def headers_for(report_type: str) -> list[str]:
        return REPORT_HEADERS[locale][report_type]
    if payload.report_type == "attendance":
        criteria = attendance_criteria(
            company_id,
            payload.date_from,
            payload.date_to,
            payload.membership_id,
            payload.branch_id,
            payload.status,
            payload.shift_id,
            payload.department_id,
        )
        if visible_members is not None:
            criteria.append(AttendanceRecord.membership_id.in_(visible_members))
        records = await session.scalars(
            select(AttendanceRecord)
            .where(*criteria)
            .order_by(AttendanceRecord.work_date.desc())
            .limit(10000)
        )
        return headers_for("attendance"), [
            [
                item.work_date.isoformat(),
                mapped_name(item.membership_id, employee_names, "الموظف" if locale == "ar" else "Employee"),
                mapped_name(item.branch_id, branch_names, "الفرع" if locale == "ar" else "Branch"),
                mapped_name(item.shift_id, shift_names, "الوردية" if locale == "ar" else "Shift"),
                value_label(item.status, locale),
                format_report_datetime(item.checked_in_at, branch_timezones.get(str(item.branch_id), "Asia/Riyadh")),
                format_report_datetime(item.checked_out_at, branch_timezones.get(str(item.branch_id), "Asia/Riyadh")),
                f"{item.worked_minutes} {'دقيقة' if locale == 'ar' else 'min'}",
                f"{item.late_minutes} {'دقيقة' if locale == 'ar' else 'min'}",
                f"{item.early_departure_minutes} {'دقيقة' if locale == 'ar' else 'min'}",
            ]
            for item in records
        ]
    if payload.report_type == "geofence_exits":
        criteria = [GeofenceExitEvent.company_id == company_id]
        if visible_members is not None:
            criteria.append(GeofenceExitEvent.membership_id.in_(visible_members))
        if payload.membership_id:
            criteria.append(GeofenceExitEvent.membership_id == payload.membership_id)
        if payload.branch_id:
            criteria.append(GeofenceExitEvent.branch_id == payload.branch_id)
        if payload.shift_id:
            criteria.append(GeofenceExitEvent.shift_id == payload.shift_id)
        if payload.status:
            criteria.append(GeofenceExitEvent.status == payload.status)
        items = await session.scalars(
            select(GeofenceExitEvent)
            .where(*criteria)
            .order_by(GeofenceExitEvent.detected_at.desc())
            .limit(10000)
        )
        return headers_for("geofence_exits"), [
            [
                format_report_datetime(item.detected_at, branch_timezones.get(str(item.branch_id), "Asia/Riyadh")),
                mapped_name(item.membership_id, employee_names, "الموظف" if locale == "ar" else "Employee"),
                mapped_name(item.branch_id, branch_names, "الفرع" if locale == "ar" else "Branch"),
                mapped_name(item.shift_id, shift_names, "الوردية" if locale == "ar" else "Shift"),
                value_label(item.status, locale),
                f"{item.distance_m or 0} m",
                f"{item.accuracy_m or 0} m",
                item.review_comment or "—",
            ]
            for item in items
        ]
    if payload.report_type == "leave":
        leave_criteria: list[Any] = [LeaveRequest.company_id == company_id]
        if visible_members is not None:
            leave_criteria.append(LeaveRequest.membership_id.in_(visible_members))
        if payload.date_from:
            leave_criteria.append(LeaveRequest.ends_on >= payload.date_from)
        if payload.date_to:
            leave_criteria.append(LeaveRequest.starts_on <= payload.date_to)
        if payload.status:
            leave_criteria.append(LeaveRequest.status == payload.status)
        leave_items = await session.scalars(
            select(LeaveRequest)
            .where(*leave_criteria)
            .order_by(LeaveRequest.created_at.desc())
            .limit(10000)
        )
        return headers_for("leave"), [
            [
                mapped_name(item.membership_id, employee_names, "الموظف" if locale == "ar" else "Employee"),
                item.starts_on.isoformat(),
                item.ends_on.isoformat(),
                f"{item.days} {'يوم' if locale == 'ar' else 'days'}",
                value_label(item.status, locale),
                item.reason,
            ]
            for item in leave_items
        ]
    if payload.report_type == "permissions":
        permission_criteria: list[Any] = [PermissionRequest.company_id == company_id]
        if visible_members is not None:
            permission_criteria.append(PermissionRequest.membership_id.in_(visible_members))
        if payload.date_from:
            permission_criteria.append(
                PermissionRequest.ends_at
                >= datetime.combine(payload.date_from, datetime.min.time(), UTC)
            )
        if payload.date_to:
            permission_criteria.append(
                PermissionRequest.starts_at
                < datetime.combine(
                    payload.date_to + timedelta(days=1), datetime.min.time(), UTC
                )
            )
        if payload.status:
            permission_criteria.append(PermissionRequest.status == payload.status)
        permission_items = await session.scalars(
            select(PermissionRequest)
            .where(*permission_criteria)
            .order_by(PermissionRequest.created_at.desc())
            .limit(10000)
        )
        return headers_for("permissions"), [
            [
                mapped_name(item.membership_id, employee_names, "الموظف" if locale == "ar" else "Employee"),
                value_label(item.request_type, locale),
                format_report_datetime(item.starts_at, "Asia/Riyadh"),
                format_report_datetime(item.ends_at, "Asia/Riyadh"),
                value_label(item.status, locale),
                item.reason,
            ]
            for item in permission_items
        ]
    if payload.report_type == "tasks":
        task_criteria: list[Any] = [WorkTask.company_id == company_id]
        if visible_members is not None:
            task_criteria.append(
                WorkTask.id.in_(
                    select(TaskAssignee.task_id).where(
                        TaskAssignee.membership_id.in_(visible_members)
                    )
                )
            )
        if payload.date_from:
            task_criteria.append(
                WorkTask.created_at
                >= datetime.combine(payload.date_from, datetime.min.time(), UTC)
            )
        if payload.date_to:
            task_criteria.append(
                WorkTask.created_at
                < datetime.combine(
                    payload.date_to + timedelta(days=1), datetime.min.time(), UTC
                )
            )
        if payload.status:
            task_criteria.append(WorkTask.status == payload.status)
        completion_time = (
            select(func.max(TaskStatusHistory.created_at))
            .where(
                TaskStatusHistory.company_id == WorkTask.company_id,
                TaskStatusHistory.task_id == WorkTask.id,
                TaskStatusHistory.new_status == "completed",
            )
            .correlate(WorkTask)
            .scalar_subquery()
        )
        task_items = await session.execute(
            select(WorkTask, completion_time.label("completed_at"))
            .where(*task_criteria)
            .order_by(WorkTask.created_at.desc())
            .limit(10000)
        )
        return headers_for("tasks"), [
            [
                item.title,
                format_report_datetime(item.created_at, "Asia/Riyadh"),
                format_report_datetime(completed_at, "Asia/Riyadh"),
                format_report_datetime(item.due_at, "Asia/Riyadh"),
                value_label(item.priority, locale),
                value_label(item.status, locale),
                mapped_name(item.created_by_membership_id, employee_names, "الموظف" if locale == "ar" else "Employee"),
            ]
            for item, completed_at in task_items
        ]
    if payload.report_type == "documents":
        document_criteria: list[Any] = [EmployeeDocument.company_id == company_id]
        if visible_members is not None:
            document_criteria.append(EmployeeDocument.membership_id.in_(visible_members))
        if payload.date_from:
            document_criteria.append(EmployeeDocument.expires_on >= payload.date_from)
        if payload.date_to:
            document_criteria.append(EmployeeDocument.expires_on <= payload.date_to)
        if payload.status:
            document_criteria.append(EmployeeDocument.review_status == payload.status)
        document_items = await session.scalars(
            select(EmployeeDocument)
            .where(*document_criteria)
            .order_by(EmployeeDocument.expires_on.asc().nullslast())
            .limit(10000)
        )
        return headers_for("documents"), [
            [
                mapped_name(item.membership_id, employee_names, "الموظف" if locale == "ar" else "Employee"),
                value_label(item.document_type, locale),
                item.document_number or "—",
                format_report_date(item.issued_on),
                format_report_date(item.expires_on),
                value_label(item.review_status, locale),
            ]
            for item in document_items
        ]
    if payload.report_type == "branches":
        branch_items = await session.scalars(
            select(Branch)
            .where(
                Branch.company_id == company_id,
                *([] if visible_branches is None else [Branch.id.in_(visible_branches)]),
            )
            .order_by(Branch.name.asc())
        )
        return headers_for("branches"), [
            [
                item.code,
                item.name,
                item.full_address or "—",
                item.timezone,
                f"{item.geofence_radius_m} m",
                value_label("active" if item.is_active else "inactive", locale),
            ]
            for item in branch_items
        ]
    shift_items = await session.scalars(
        select(Shift).where(Shift.company_id == company_id).order_by(Shift.name.asc())
    )
    return headers_for("shifts"), [
        [
            item.code,
            item.name,
            item.start_time.isoformat(),
            item.end_time.isoformat(),
            value_label("yes" if item.is_overnight else "no", locale),
            f"{item.grace_period_minutes} {'دقيقة' if locale == 'ar' else 'min'}",
            value_label("active" if item.is_active else "inactive", locale),
        ]
        for item in shift_items
    ]


def create_xlsx(
    headers: list[str],
    rows: list[list[object]],
    *,
    company_identity: str = "HADIR",
    report_title: str = "HADIR Report",
    locale: str = "en",
) -> bytes:
    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet("HADIR Report")
    worksheet.append([safe_spreadsheet_value(company_identity)])
    worksheet.append([safe_spreadsheet_value(report_title)])
    worksheet.append(["تاريخ إنشاء الملف" if locale == "ar" else "File generated", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")])
    worksheet.append(headers)
    for row in rows:
        worksheet.append([safe_spreadsheet_value(value) for value in row])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def create_combined_xlsx(
    sections: list[tuple[str, list[str], list[list[object]]]],
    *,
    company_identity: str = "HADIR",
    locale: str = "en",
) -> bytes:
    workbook = Workbook(write_only=True)
    for index, (title, headers, rows) in enumerate(sections, start=1):
        worksheet = workbook.create_sheet(f"{index} - {title}"[:31])
        worksheet.append([safe_spreadsheet_value(company_identity)])
        worksheet.append([title])
        worksheet.append(["تاريخ إنشاء الملف" if locale == "ar" else "File generated", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")])
        worksheet.append(headers)
        for row in rows:
            worksheet.append([safe_spreadsheet_value(value) for value in row])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def safe_spreadsheet_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = "".join(character for character in value if character >= " " or character == "\t")
    if normalized.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{normalized}"
    return normalized


def _pdf_font(locale: str) -> str:
    """Return a font that can display the selected report language."""
    if locale != "ar":
        return "Helvetica"
    candidates = (
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    )
    for font_path in candidates:
        path = Path(font_path)
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("HadirArabic", str(path)))
                return "HadirArabic"
            except Exception:
                continue
    return "Helvetica"


def _pdf_text(value: object, locale: str) -> str:
    text = str(value if value is not None else "—")
    if locale == "ar" and arabic_reshaper is not None and bidi_display is not None:
        try:
            return bidi_display(arabic_reshaper.reshape(text))
        except Exception:
            pass
    return text


def _pdf_paragraph(value: object, style: ParagraphStyle, locale: str) -> Paragraph:
    return Paragraph(escape(_pdf_text(value, locale)).replace("\n", "<br/>") , style)


def _report_period(date_from: date | None, date_to: date | None, locale: str) -> str:
    if date_from and date_to:
        return (
            f"من {date_from:%Y-%m-%d} إلى {date_to:%Y-%m-%d}"
            if locale == "ar"
            else f"{date_from:%Y-%m-%d} to {date_to:%Y-%m-%d}"
        )
    if date_from:
        return f"من {date_from:%Y-%m-%d}" if locale == "ar" else f"From {date_from:%Y-%m-%d}"
    if date_to:
        return f"حتى {date_to:%Y-%m-%d}" if locale == "ar" else f"Through {date_to:%Y-%m-%d}"
    return "كل التواريخ" if locale == "ar" else "All dates"


def _pdf_logo(company_logo: bytes | None) -> Image | None:
    """Build a proportional logo flowable, ignoring corrupt/unsupported uploads."""
    if not company_logo:
        return None
    try:
        reader = ImageReader(BytesIO(company_logo))
        width, height = reader.getSize()
        if not width or not height:
            return None
        max_width = 30 * mm
        max_height = 22 * mm
        scale = min(max_width / width, max_height / height)
        logo = Image(BytesIO(company_logo), width=width * scale, height=height * scale)
        logo.hAlign = "CENTER"
        return logo
    except Exception:
        return None


def create_pdf(
    title: str,
    headers: list[str],
    rows: list[list[object]],
    *,
    company_name: str,
    company_registration_number: str | None,
    company_unified_number: str | None,
    company_contact_phone: str | None = None,
    company_tax_number: str | None = None,
    company_logo: bytes | None = None,
    company_timezone: str,
    date_from: date | None,
    date_to: date | None,
    locale: str,
    sections: list[tuple[str, list[str], list[list[object]]]] | None = None,
) -> bytes:
    """Create a client-facing report instead of a raw pipe-delimited dump."""
    buffer = BytesIO()
    page_width, _ = landscape(A4)
    font_name = _pdf_font(locale)
    direction_alignment = TA_CENTER
    title_style = ParagraphStyle(
        "HadirReportTitle",
        fontName=font_name,
        fontSize=16,
        leading=20,
        alignment=direction_alignment,
        textColor=colors.HexColor("#075f59"),
        spaceAfter=3 * mm,
    )
    company_style = ParagraphStyle(
        "HadirReportCompany",
        fontName=font_name,
        fontSize=10,
        leading=13,
        alignment=direction_alignment,
        textColor=colors.HexColor("#344e4b"),
        spaceAfter=5 * mm,
    )
    company_corner_style = ParagraphStyle(
        "HadirReportCompanyCorner",
        fontName=font_name,
        fontSize=8.5,
        leading=11,
        alignment=TA_RIGHT if locale == "ar" else TA_LEFT,
        textColor=colors.HexColor("#344e4b"),
        spaceAfter=1.5 * mm,
        wordWrap="CJK",
    )
    meta_label_style = ParagraphStyle(
        "HadirReportMetaLabel",
        fontName=font_name,
        fontSize=7.5,
        leading=10,
        alignment=direction_alignment,
        textColor=colors.HexColor("#4f6b68"),
    )
    meta_value_style = ParagraphStyle(
        "HadirReportMetaValue",
        fontName=font_name,
        fontSize=8.5,
        leading=11,
        alignment=direction_alignment,
        textColor=colors.HexColor("#173330"),
    )
    cell_style = ParagraphStyle(
        "HadirReportCell",
        fontName=font_name,
        fontSize=7.2,
        leading=9,
        alignment=direction_alignment,
        textColor=colors.HexColor("#173330"),
        wordWrap="CJK",
    )
    header_style = ParagraphStyle(
        "HadirReportHeader",
        fontName=font_name,
        fontSize=7.4,
        leading=9,
        alignment=direction_alignment,
        textColor=colors.white,
        wordWrap="CJK",
    )
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=17 * mm,
        title=title,
        author="HADIR",
    )
    generated_at = datetime.now(UTC)
    try:
        generated_local = generated_at.astimezone(ZoneInfo(company_timezone))
    except (ValueError, TypeError):
        generated_local = generated_at
    generated_label = generated_local.strftime("%Y-%m-%d %H:%M")
    period_label = _report_period(date_from, date_to, locale)
    if locale == "ar":
        period_name, generated_name, total_name = "فترة التقرير", "تاريخ إنشاء الملف", "عدد السجلات"
    else:
        period_name, generated_name, total_name = "Report period", "File generated", "Total records"

    report_sections = sections or [(title, headers, rows)]
    company_identity = company_name
    identity_parts = []
    if company_registration_number:
        identity_parts.append(
            f"{'السجل التجاري' if locale == 'ar' else 'CR'}: {company_registration_number}"
        )
    if company_unified_number:
        identity_parts.append(
            f"{'الرقم الموحد' if locale == 'ar' else 'Unified number'}: {company_unified_number}"
        )
    if identity_parts:
        company_identity = f"{company_name} · {' · '.join(identity_parts)}"
    header_details: list[str] = []
    if company_contact_phone:
        header_details.append(
            f"{'الجوال' if locale == 'ar' else 'Phone'}: {company_contact_phone}"
        )
    if company_tax_number:
        header_details.append(
            f"{'الرقم الضريبي' if locale == 'ar' else 'Tax number'}: {company_tax_number}"
        )
    # Keep the report title centered while reserving the two physical corners
    # for branding: the logo on the left and a readable company identity block
    # on the right. This remains clear in both Arabic and English PDFs.
    center_stack: list[object] = [_pdf_paragraph(title, title_style, locale)]
    company_info_stack: list[object] = [
        _pdf_paragraph(company_name, company_corner_style, locale),
    ]
    for identity_part in identity_parts:
        company_info_stack.append(_pdf_paragraph(identity_part, company_corner_style, locale))
    for detail in header_details:
        company_info_stack.append(_pdf_paragraph(detail, company_corner_style, locale))
    logo = _pdf_logo(company_logo)
    available_width = page_width - 28 * mm
    side_width = 42 * mm
    info_width = 96 * mm
    center_width = available_width - side_width - info_width
    logo_cell: object = logo if logo is not None else Spacer(1, 22 * mm)
    header = Table(
        [[logo_cell, center_stack, company_info_stack]],
        colWidths=[side_width, center_width, info_width],
        hAlign="CENTER",
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8dedb")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5faf9")),
        ("LINEAFTER", (0, 0), (1, 0), 0.25, colors.HexColor("#d7e8e5")),
        ("LINEAFTER", (1, 0), (1, 0), 0.25, colors.HexColor("#d7e8e5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story: list[object] = [header]
    metadata = Table(
        [[
            _pdf_paragraph(period_name, meta_label_style, locale),
            _pdf_paragraph(period_label, meta_value_style, locale),
            _pdf_paragraph(generated_name, meta_label_style, locale),
            _pdf_paragraph(generated_label, meta_value_style, locale),
            _pdf_paragraph(total_name, meta_label_style, locale),
            _pdf_paragraph(str(sum(len(section_rows) for _, _, section_rows in report_sections)), meta_value_style, locale),
        ]],
        colWidths=[24 * mm, 42 * mm, 25 * mm, 39 * mm, 25 * mm, 18 * mm],
    )
    metadata.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#edf6f4")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8dedb")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d7e8e5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([metadata, Spacer(1, 6 * mm)])
    for section_index, (section_title, section_headers, section_rows) in enumerate(report_sections):
        if len(report_sections) > 1:
            story.append(_pdf_paragraph(section_title, company_style, locale))
        if section_rows:
            table_data = [[_pdf_paragraph(header, header_style, locale) for header in section_headers]]
            table_data.extend([
                [_pdf_paragraph(value, cell_style, locale) for value in row]
                for row in section_rows
            ])
            available_width = page_width - 28 * mm
            weights = [1.1 if len(section_headers) <= 7 else 1 for _ in section_headers]
            if section_headers:
                weights[0] = 1.25
            total_weight = sum(weights) or 1
            table = Table(
                table_data,
                repeatRows=1,
                colWidths=[available_width * weight / total_weight for weight in weights],
                hAlign="CENTER",
            )
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#075f59")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8dedb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5faf9")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(table)
        elif len(report_sections) == 1:
            empty_label = "لا توجد سجلات ضمن الفترة المحددة." if locale == "ar" else "No records found for the selected period."
            empty_style = ParagraphStyle(
                "HadirReportEmpty",
                parent=cell_style,
                fontSize=11,
                leading=15,
                textColor=colors.HexColor("#4f6b68"),
                spaceBefore=12 * mm,
                spaceAfter=12 * mm,
            )
            story.append(_pdf_paragraph(empty_label, empty_style, locale))
        if section_index < len(report_sections) - 1:
            story.append(Spacer(1, 8 * mm))
    if not report_sections:
        empty_label = "لا توجد سجلات ضمن الفترة المحددة." if locale == "ar" else "No records found for the selected period."
        empty_style = ParagraphStyle(
            "HadirReportEmpty",
            parent=cell_style,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#4f6b68"),
            spaceBefore=12 * mm,
            spaceAfter=12 * mm,
        )
        story.append(_pdf_paragraph(empty_label, empty_style, locale))

    footer_title = _pdf_text(title, locale)
    footer_company = _pdf_text(company_name, locale)

    def draw_footer(canv, doc) -> None:
        canv.saveState()
        canv.setFont(font_name, 7)
        canv.setFillColor(colors.HexColor("#5f7774"))
        canv.drawString(14 * mm, 9 * mm, f"{footer_company} · {footer_title}")
        page_label = f"{('صفحة' if locale == 'ar' else 'Page')} {doc.page}"
        canv.drawRightString(page_width - 14 * mm, 9 * mm, _pdf_text(page_label, locale))
        canv.restoreState()

    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buffer.getvalue()


@router.post("/exports", response_model=ExportJobResponse, status_code=201)
async def create_export(
    payload: ExportCreateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey = None,
) -> ExportJobResponse:
    context = tenant_context(auth_session)
    idempotency, replay = await begin_idempotency(
        session, context, "reports.export", idempotency_key, payload
    )
    if replay is not None:
        return ExportJobResponse.model_validate(replay)
    await require_permission(session, context, Permission.REPORTS_EXPORT)
    if payload.membership_id is not None:
        await require_membership_scope(session, context, payload.membership_id)
    if payload.branch_id is not None:
        await require_branch_scope(session, context, payload.branch_id)
    if payload.department_id is not None:
        await require_department_scope(session, context, payload.department_id)
    if payload.group_id is not None:
        await require_group_scope(session, context, payload.group_id)
    subscription = await active_subscription(session, context.company_id)
    if subscription is None or subscription[1].features.get("reports") not in {
        "basic",
        "advanced",
    }:
        raise ProblemError(
            status=403,
            code="subscription_feature_unavailable",
            title="Report exports are unavailable",
            detail="The current subscription does not include report exports.",
        )
    report_types = list(dict.fromkeys([payload.report_type, *payload.report_types]))
    filters = payload.model_dump(mode="json", exclude={"report_type", "export_format"})
    filters["report_types"] = report_types
    job = ExportJob(
        company_id=context.company_id,
        requested_by_membership_id=context.membership.id,
        report_type=payload.report_type if len(report_types) == 1 else "bundle",
        export_format=payload.export_format,
        filters=filters,
        status="processing",
        progress_percent=10,
    )
    session.add(job)
    await session.flush()
    try:
        visible = await report_membership_scope(
            session,
            context,
            membership_id=payload.membership_id,
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            group_id=payload.group_id,
        )
        scopes = await membership_scopes(session, context)
        display_maps = await report_display_maps(session, context.company_id)
        company_logo: bytes | None = None
        if context.company.logo_file_id is not None:
            logo_file = await session.scalar(
                select(StoredFile).where(
                    StoredFile.company_id == context.company_id,
                    StoredFile.id == context.company.logo_file_id,
                )
            )
            if logo_file is not None and logo_file.content_type.startswith("image/"):
                company_logo = logo_file.content
        sections: list[tuple[str, list[str], list[list[object]]]] = []
        for report_type in report_types:
            section_payload = payload.model_copy(update={"report_type": report_type})
            section_headers, section_rows = await export_rows(
                session,
                context.company_id,
                section_payload,
                visible,
                None if scopes.unrestricted else scopes.branch_ids,
                display_maps,
            )
            sections.append((REPORT_TITLES[payload.locale][report_type], section_headers, section_rows))
        job.progress_percent = 60
        company_identity = context.company.display_name
        if context.company.commercial_registration_number:
            company_identity += f" · {'السجل التجاري' if payload.locale == 'ar' else 'CR'}: {context.company.commercial_registration_number}"
        if context.company.unified_number:
            company_identity += f" · {'الرقم الموحد' if payload.locale == 'ar' else 'Unified number'}: {context.company.unified_number}"
        if context.company.contact_phone:
            company_identity += f" · {'الجوال' if payload.locale == 'ar' else 'Phone'}: {context.company.contact_phone}"
        if context.company.tax_number:
            company_identity += f" · {'الرقم الضريبي' if payload.locale == 'ar' else 'Tax number'}: {context.company.tax_number}"
        if payload.export_format == "xlsx":
            job.file_content = (
                create_xlsx(
                    *sections[0][1:],
                    company_identity=company_identity,
                    report_title=sections[0][0],
                    locale=payload.locale,
                )
                if len(sections) == 1
                else create_combined_xlsx(
                    sections,
                    company_identity=company_identity,
                    locale=payload.locale,
                )
            )
            job.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            job.file_content = create_pdf(
                "تقرير مجمع" if len(sections) > 1 and payload.locale == "ar" else "Combined report" if len(sections) > 1 else sections[0][0],
                sections[0][1],
                sections[0][2],
                company_name=context.company.display_name,
                company_registration_number=context.company.commercial_registration_number,
                company_unified_number=context.company.unified_number,
                company_contact_phone=context.company.contact_phone,
                company_tax_number=context.company.tax_number,
                company_logo=company_logo,
                company_timezone=context.company.timezone,
                date_from=payload.date_from,
                date_to=payload.date_to,
                locale=payload.locale,
                sections=sections if len(sections) > 1 else None,
            )
            job.content_type = "application/pdf"
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        arabic_filename_slugs = {
            "attendance": "الحضور-والانصراف",
            "geofence_exits": "مغادرة-النطاق",
            "leave": "الإجازات",
            "permissions": "الاستئذانات",
            "tasks": "المهام",
            "documents": "وثائق-الموظفين",
            "branches": "الفروع",
            "shifts": "الورديات",
        }
        filename_title = (
            "تقرير-مجمع"
            if len(report_types) > 1 and payload.locale == "ar"
            else "hadir-combined-report"
            if len(report_types) > 1
            else arabic_filename_slugs[payload.report_type]
            if payload.locale == "ar"
            else f"hadir-{payload.report_type}"
        )
        job.filename = f"{filename_title}-{timestamp}.{payload.export_format}"
        job.status = "completed"
        job.progress_percent = 100
        job.completed_at = datetime.now(UTC)
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:1000]
        job.progress_percent = 100
    result = export_response(job)
    complete_idempotency(idempotency, result, status.HTTP_201_CREATED)
    await session.commit()
    return result


@router.get("/exports", response_model=list[ExportJobResponse])
async def list_exports(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[ExportJobResponse]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_EXPORT)
    scopes = await membership_scopes(session, context)
    expired = await expire_export_jobs(
        session,
        context.company_id,
        requested_by_membership_id=None if scopes.unrestricted else context.membership.id,
    )
    if expired:
        await session.commit()
    criteria = [ExportJob.company_id == context.company_id]
    if not scopes.unrestricted:
        criteria.append(ExportJob.requested_by_membership_id == context.membership.id)
    jobs = await session.scalars(
        select(ExportJob).where(*criteria).order_by(ExportJob.created_at.desc()).limit(100)
    )
    return [export_response(job) for job in jobs]


@router.post("/exports/cleanup")
async def cleanup_exports(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> dict[str, int]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_EXPORT)
    scopes = await membership_scopes(session, context)
    cleaned = await expire_export_jobs(
        session,
        context.company_id,
        requested_by_membership_id=None if scopes.unrestricted else context.membership.id,
    )
    await session.commit()
    return {"cleaned": cleaned}


@router.get("/exports/{job_id}/download")
async def download_export(
    job_id: UUID, auth_session: CurrentAuthSession, session: DatabaseSession
) -> Response:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_EXPORT)
    scopes = await membership_scopes(session, context)
    criteria = [ExportJob.company_id == context.company_id, ExportJob.id == job_id]
    if not scopes.unrestricted:
        criteria.append(ExportJob.requested_by_membership_id == context.membership.id)
    job = await session.scalar(select(ExportJob).where(*criteria))
    if job is not None and (job.status == "expired" or job.expires_at <= datetime.now(UTC)):
        job.status = "expired"
        job.file_content = None
        job.content_type = None
        await session.commit()
        raise ProblemError(
            status=status.HTTP_410_GONE,
            code="export_expired",
            title="Export expired",
            detail="The export retention period ended. Create a new export.",
        )
    if job is None or job.file_content is None or job.content_type is None or job.filename is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="export_not_found",
            title="Export not found",
            detail="The completed export does not exist in this company.",
        )
    return Response(
        content=job.file_content,
        media_type=job.content_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="hadir-report.{job.export_format}"; '
                f"filename*=UTF-8''{quote(job.filename)}"
            )
        },
    )
