from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from openpyxl import Workbook
from pydantic import BaseModel, ConfigDict, Field
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    membership_scopes,
    require_branch_scope,
    require_membership_scope,
    require_permission,
    tenant_context,
    visible_membership_ids,
)
from app.core.errors import ProblemError
from app.core.subscription_catalog import active_subscription
from app.db.session import get_session
from app.models.attendance import AttendanceRecord, PermissionRequest
from app.models.organization import Branch, EmployeeBranchAssignment, EmployeeProfile, Shift
from app.models.platform import AttendanceLeaderboardSetting, ExportJob
from app.models.workforce import EmployeeDocument, LeaveRequest, TaskAssignee, WorkTask

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


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


class ExportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_type: Literal[
        "attendance", "leave", "permissions", "tasks", "documents", "branches", "shifts"
    ]
    export_format: Literal["pdf", "xlsx"]
    date_from: date | None = None
    date_to: date | None = None
    membership_id: UUID | None = None
    branch_id: UUID | None = None
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
    created_at: datetime


class LeaderboardSettingRequest(BaseModel):
    visibility: Literal["manager_only", "branch", "company", "disabled"]
    enabled: bool


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
    await session.commit()
    return {"visibility": item.visibility, "enabled": item.enabled}


@router.get("/leaderboard", response_model=list[LeaderboardItem])
async def attendance_leaderboard(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[LeaderboardItem]:
    context = tenant_context(auth_session)
    setting = await session.get(AttendanceLeaderboardSetting, context.company_id)
    if setting is None or not setting.enabled or setting.visibility == "disabled":
        return []
    manager = context.membership.role_code in {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    if setting.visibility == "manager_only" and not manager:
        return []
    criteria: list[Any] = [
        AttendanceRecord.company_id == context.company_id,
        AttendanceRecord.status.in_(("on_time", "late", "on_permission")),
        AttendanceRecord.work_date >= date.today() - timedelta(days=30),
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
            display_name=row[0],
            on_time_days=int(row[1]),
            worked_minutes=int(row[2]),
        )
        for index, row in enumerate(rows, start=1)
    ]


def export_response(job: ExportJob) -> ExportJobResponse:
    return ExportJobResponse.model_validate(job, from_attributes=True)


def attendance_criteria(
    company_id: UUID,
    date_from: date | None,
    date_to: date | None,
    membership_id: UUID | None,
    branch_id: UUID | None,
    record_status: str | None,
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
    return criteria


@router.get("/attendance", response_model=AttendanceReportResponse)
async def attendance_report(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
    membership_id: UUID | None = None,
    branch_id: UUID | None = None,
    record_status: Annotated[str | None, Query(alias="status")] = None,
) -> AttendanceReportResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_VIEW)
    if membership_id is not None:
        await require_membership_scope(session, context, membership_id)
    if branch_id is not None:
        await require_branch_scope(session, context, branch_id)
    criteria = attendance_criteria(
        context.company_id, date_from, date_to, membership_id, branch_id, record_status
    )
    visible = await visible_membership_ids(session, context)
    if visible is not None:
        criteria.append(AttendanceRecord.membership_id.in_(visible))
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
    )


async def export_rows(
    session: AsyncSession,
    company_id: UUID,
    payload: ExportCreateRequest,
    visible_members: frozenset[UUID] | None,
    visible_branches: frozenset[UUID] | None,
) -> tuple[list[str], list[list[object]]]:
    if payload.report_type == "attendance":
        criteria = attendance_criteria(
            company_id,
            payload.date_from,
            payload.date_to,
            payload.membership_id,
            payload.branch_id,
            payload.status,
        )
        if visible_members is not None:
            criteria.append(AttendanceRecord.membership_id.in_(visible_members))
        records = await session.scalars(
            select(AttendanceRecord)
            .where(*criteria)
            .order_by(AttendanceRecord.work_date.desc())
            .limit(10000)
        )
        return [
            "Date",
            "Employee",
            "Branch",
            "Shift",
            "Status",
            "Check in",
            "Check out",
            "Worked min",
            "Late min",
            "Early min",
        ], [
            [
                item.work_date.isoformat(),
                str(item.membership_id),
                str(item.branch_id),
                str(item.shift_id),
                item.status,
                item.checked_in_at.isoformat() if item.checked_in_at else "",
                item.checked_out_at.isoformat() if item.checked_out_at else "",
                item.worked_minutes,
                item.late_minutes,
                item.early_departure_minutes,
            ]
            for item in records
        ]
    if payload.report_type == "leave":
        leave_items = await session.scalars(
            select(LeaveRequest)
            .where(
                LeaveRequest.company_id == company_id,
                *(
                    []
                    if visible_members is None
                    else [LeaveRequest.membership_id.in_(visible_members)]
                ),
            )
            .order_by(LeaveRequest.created_at.desc())
            .limit(10000)
        )
        return ["Employee", "From", "To", "Days", "Status", "Reason"], [
            [
                str(item.membership_id),
                item.starts_on.isoformat(),
                item.ends_on.isoformat(),
                item.days,
                item.status,
                item.reason,
            ]
            for item in leave_items
        ]
    if payload.report_type == "permissions":
        permission_items = await session.scalars(
            select(PermissionRequest)
            .where(
                PermissionRequest.company_id == company_id,
                *(
                    []
                    if visible_members is None
                    else [PermissionRequest.membership_id.in_(visible_members)]
                ),
            )
            .order_by(PermissionRequest.created_at.desc())
            .limit(10000)
        )
        return ["Employee", "Type", "From", "To", "Status", "Reason"], [
            [
                str(item.membership_id),
                item.request_type,
                item.starts_at.isoformat(),
                item.ends_at.isoformat(),
                item.status,
                item.reason,
            ]
            for item in permission_items
        ]
    if payload.report_type == "tasks":
        task_items = await session.scalars(
            select(WorkTask)
            .where(
                WorkTask.company_id == company_id,
                *(
                    []
                    if visible_members is None
                    else [
                        WorkTask.id.in_(
                            select(TaskAssignee.task_id).where(
                                TaskAssignee.membership_id.in_(visible_members)
                            )
                        )
                    ]
                ),
            )
            .order_by(WorkTask.created_at.desc())
            .limit(10000)
        )
        return ["Title", "Priority", "Due", "Status", "Created by"], [
            [
                item.title,
                item.priority,
                item.due_at.isoformat() if item.due_at else "",
                item.status,
                str(item.created_by_membership_id),
            ]
            for item in task_items
        ]
    if payload.report_type == "documents":
        document_items = await session.scalars(
            select(EmployeeDocument)
            .where(
                EmployeeDocument.company_id == company_id,
                *(
                    []
                    if visible_members is None
                    else [EmployeeDocument.membership_id.in_(visible_members)]
                ),
            )
            .order_by(EmployeeDocument.expires_on.asc().nullslast())
            .limit(10000)
        )
        return ["Employee", "Type", "Number", "Issued", "Expires", "Review"], [
            [
                str(item.membership_id),
                item.document_type,
                item.document_number or "",
                item.issued_on.isoformat() if item.issued_on else "",
                item.expires_on.isoformat() if item.expires_on else "",
                item.review_status,
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
        return ["Code", "Name", "Address", "Timezone", "Radius m", "Active"], [
            [
                item.code,
                item.name,
                item.full_address,
                item.timezone,
                item.geofence_radius_m,
                item.is_active,
            ]
            for item in branch_items
        ]
    shift_items = await session.scalars(
        select(Shift).where(Shift.company_id == company_id).order_by(Shift.name.asc())
    )
    return ["Code", "Name", "Start", "End", "Overnight", "Grace", "Active"], [
        [
            item.code,
            item.name,
            item.start_time.isoformat(),
            item.end_time.isoformat(),
            item.is_overnight,
            item.grace_period_minutes,
            item.is_active,
        ]
        for item in shift_items
    ]


def create_xlsx(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet("HADIR Report")
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def create_pdf(title: str, headers: list[str], rows: list[list[object]]) -> bytes:
    buffer = BytesIO()
    document = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    y = height - 36
    document.setTitle(title)
    document.setFont("Helvetica-Bold", 14)
    document.drawString(30, y, title)
    y -= 24
    document.setFont("Helvetica-Bold", 7)
    document.drawString(30, y, " | ".join(headers)[:180])
    y -= 14
    document.setFont("Helvetica", 7)
    for row in rows:
        if y < 30:
            document.showPage()
            y = height - 36
            document.setFont("Helvetica", 7)
        document.drawString(30, y, " | ".join(str(value) for value in row)[:190])
        y -= 11
    document.save()
    return buffer.getvalue()


@router.post("/exports", response_model=ExportJobResponse, status_code=201)
async def create_export(
    payload: ExportCreateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> ExportJobResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_EXPORT)
    if payload.membership_id is not None:
        await require_membership_scope(session, context, payload.membership_id)
    if payload.branch_id is not None:
        await require_branch_scope(session, context, payload.branch_id)
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
    filters = payload.model_dump(mode="json", exclude={"report_type", "export_format"})
    job = ExportJob(
        company_id=context.company_id,
        requested_by_membership_id=context.membership.id,
        report_type=payload.report_type,
        export_format=payload.export_format,
        filters=filters,
        status="processing",
        progress_percent=10,
    )
    session.add(job)
    await session.flush()
    try:
        visible = await visible_membership_ids(session, context)
        scopes = await membership_scopes(session, context)
        headers, rows = await export_rows(
            session,
            context.company_id,
            payload,
            visible,
            None if scopes.unrestricted else scopes.branch_ids,
        )
        job.progress_percent = 60
        if payload.export_format == "xlsx":
            job.file_content = create_xlsx(headers, rows)
            job.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            job.file_content = create_pdf(
                f"HADIR {payload.report_type.title()} Report", headers, rows
            )
            job.content_type = "application/pdf"
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        job.filename = f"hadir-{payload.report_type}-{timestamp}.{payload.export_format}"
        job.status = "completed"
        job.progress_percent = 100
        job.completed_at = datetime.now(UTC)
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:1000]
        job.progress_percent = 100
    await session.commit()
    await session.refresh(job)
    return export_response(job)


@router.get("/exports", response_model=list[ExportJobResponse])
async def list_exports(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[ExportJobResponse]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_EXPORT)
    scopes = await membership_scopes(session, context)
    criteria = [ExportJob.company_id == context.company_id]
    if not scopes.unrestricted:
        criteria.append(ExportJob.requested_by_membership_id == context.membership.id)
    jobs = await session.scalars(
        select(ExportJob).where(*criteria).order_by(ExportJob.created_at.desc()).limit(100)
    )
    return [export_response(job) for job in jobs]


@router.get("/exports/{job_id}/download")
async def download_export(
    job_id: UUID, auth_session: CurrentAuthSession, session: DatabaseSession
) -> Response:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.REPORTS_EXPORT)
    scopes = await membership_scopes(session, context)
    criteria = [
        ExportJob.company_id == context.company_id,
        ExportJob.id == job_id,
        ExportJob.status == "completed",
    ]
    if not scopes.unrestricted:
        criteria.append(ExportJob.requested_by_membership_id == context.membership.id)
    job = await session.scalar(select(ExportJob).where(*criteria))
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
        headers={"Content-Disposition": f'attachment; filename="{job.filename}"'},
    )
