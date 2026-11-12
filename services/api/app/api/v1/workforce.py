from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    require_branch_scope,
    require_group_scope,
    require_membership_scope,
    require_permission,
    require_unrestricted_scope,
    tenant_context,
    visible_membership_ids,
)
from app.core.errors import ProblemError
from app.core.subscription_catalog import active_subscription
from app.db.session import get_session
from app.models.attendance import AttendanceRecord
from app.models.devices import AuditLog
from app.models.identity import CompanyMembership, User
from app.models.organization import (
    EmployeeBranchAssignment,
    EmployeeGroupMembership,
    EmployeeProfile,
)
from app.models.workforce import (
    EmployeeDocument,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Notification,
    NotificationPreference,
    PushDeviceToken,
    TaskAssignee,
    TaskComment,
    TaskExtensionRequest,
    TaskStatusHistory,
    WorkTask,
)
from app.services.file_access import require_owned_attachment
from app.services.idempotency import IdempotencyKey, begin_idempotency, complete_idempotency
from app.services.notification_actor import membership_actor_name
from app.services.push_delivery import FirebasePushAdapter

tasks_router = APIRouter()
leave_router = APIRouter()
documents_router = APIRouter()
notifications_router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]

TASK_STATUSES = {
    "new",
    "viewed",
    "in_progress",
    "completed",
    "postponed",
    "needs_more_time",
    "blocked",
}


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=2, max_length=10000)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    due_at: datetime | None = None
    membership_ids: list[UUID] = Field(default_factory=list, max_length=500)
    branch_id: UUID | None = None
    group_id: UUID | None = None

    @model_validator(mode="after")
    def require_target(self) -> "TaskCreateRequest":
        if not self.membership_ids and self.branch_id is None and self.group_id is None:
            raise ValueError("membership_ids, branch_id, or group_id is required")
        return self


class TaskUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    status: Literal[
        "new", "viewed", "in_progress", "completed", "postponed", "needs_more_time", "blocked"
    ]
    reason: str | None = Field(default=None, max_length=2000)
    completion_attachment_file_id: UUID | None = None
    requested_due_at: datetime | None = None

    @model_validator(mode="after")
    def require_reason(self) -> "TaskUpdateRequest":
        if self.status in {"postponed", "needs_more_time", "blocked"} and not self.reason:
            raise ValueError("reason is required for this status")
        if self.status == "needs_more_time" and self.requested_due_at is None:
            raise ValueError("requested_due_at is required when requesting more time")
        return self


class TaskManagerUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    due_at: datetime | None = None
    membership_ids: list[UUID] | None = Field(default=None, max_length=500)


class TaskCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    attachment_file_id: UUID | None = None


class TaskCommentResponse(BaseModel):
    id: UUID
    author_membership_id: UUID
    body: str
    attachment_file_id: UUID | None
    created_at: datetime


class TaskExtensionResponse(BaseModel):
    id: UUID
    requested_by_membership_id: UUID
    reason: str
    requested_due_at: datetime | None
    status: str
    decided_by_membership_id: UUID | None
    decision_comment: str | None
    approved_due_at: datetime | None
    decided_at: datetime | None
    created_at: datetime


class TaskExtensionDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    decision: Literal["approved", "rejected"]
    new_due_at: datetime | None = None
    comment: str = Field(min_length=2, max_length=2000)

    @model_validator(mode="after")
    def require_new_due_date(self) -> "TaskExtensionDecisionRequest":
        if self.decision == "approved" and self.new_due_at is None:
            raise ValueError("new_due_at is required when approving an extension")
        return self


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str
    priority: str
    due_at: datetime | None
    status: str
    created_by_membership_id: UUID
    assignee_ids: list[UUID]
    viewed_by_ids: list[UUID]
    completion_attachment_file_id: UUID | None
    latest_extension: TaskExtensionResponse | None
    version: int
    created_at: datetime
    updated_at: datetime


class TaskRecipientResponse(BaseModel):
    id: UUID
    display_name: str
    email: str
    role_code: str


class LeaveTypeRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    default_days: int = Field(ge=0, le=365)
    is_paid: bool = True


class LeaveTypeResponse(BaseModel):
    id: UUID
    code: str
    name: str
    default_days: int
    is_paid: bool
    is_active: bool


class LeaveBalanceRequest(BaseModel):
    membership_id: UUID
    leave_type_id: UUID
    year: int = Field(ge=2020, le=2100)
    allocated_days: int = Field(ge=0, le=365)
    reason: str = Field(min_length=3, max_length=1000)


class LeaveBalanceResponse(BaseModel):
    id: UUID
    membership_id: UUID
    leave_type_id: UUID
    year: int
    allocated_days: int
    used_days: int
    remaining_days: int
    version: int


class LeaveCreateRequest(BaseModel):
    leave_type_id: UUID
    starts_on: date
    ends_on: date
    reason: str = Field(min_length=3, max_length=2000)
    attachment_file_id: UUID | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "LeaveCreateRequest":
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on cannot precede starts_on")
        if self.ends_on.year != self.starts_on.year:
            raise ValueError("a leave request cannot span balance years")
        return self


class LeaveReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str | None = Field(default=None, max_length=2000)


class LeaveResponse(BaseModel):
    id: UUID
    membership_id: UUID
    leave_type_id: UUID
    starts_on: date
    ends_on: date
    days: int
    reason: str
    attachment_file_id: UUID | None
    status: str
    review_comment: str | None
    reviewed_at: datetime | None
    created_at: datetime


class DocumentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: UUID | None = None
    document_type: Literal[
        "residency",
        "passport",
        "medical_insurance",
        "employment_contract",
        "driving_license",
        "vehicle_insurance",
        "custom",
    ]
    custom_type_name: str | None = Field(default=None, max_length=160)
    document_number: str | None = Field(default=None, max_length=120)
    issued_on: date | None = None
    expires_on: date | None = None
    attachment_file_id: UUID
    reminder_days: int = Field(default=30, ge=0, le=365)

    @model_validator(mode="after")
    def validate_document(self) -> "DocumentCreateRequest":
        if self.document_type == "custom" and not self.custom_type_name:
            raise ValueError("custom_type_name is required")
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValueError("expires_on cannot precede issued_on")
        return self


class DocumentReviewRequest(BaseModel):
    decision: Literal["valid", "pending_review", "rejected"]


class DocumentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    document_type: Literal[
        "residency",
        "passport",
        "medical_insurance",
        "employment_contract",
        "driving_license",
        "vehicle_insurance",
        "custom",
    ]
    custom_type_name: str | None = Field(default=None, max_length=160)
    document_number: str | None = Field(default=None, max_length=120)
    issued_on: date | None = None
    expires_on: date | None = None
    attachment_file_id: UUID
    reminder_days: int = Field(default=30, ge=0, le=365)

    @model_validator(mode="after")
    def validate_document(self) -> "DocumentUpdateRequest":
        if self.document_type == "custom" and not self.custom_type_name:
            raise ValueError("custom_type_name is required")
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValueError("expires_on cannot precede issued_on")
        return self


class DocumentResponse(BaseModel):
    id: UUID
    membership_id: UUID
    document_type: str
    custom_type_name: str | None
    document_number: str | None
    issued_on: date | None
    expires_on: date | None
    attachment_file_id: UUID
    reminder_days: int
    status: str
    review_status: str
    version: int
    created_at: datetime
    updated_at: datetime


class NotificationResponse(BaseModel):
    id: UUID
    kind: str
    title: str
    body: str
    actor_name: str | None = None
    target_type: str | None
    target_id: UUID | None
    urgent: bool
    read_at: datetime | None
    created_at: datetime
    deep_link: str


class UnreadCountResponse(BaseModel):
    unread_count: int


class PushProviderResponse(BaseModel):
    configured: bool
    provider: str = "firebase_cloud_messaging"


class PushTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=4096)
    platform: Literal["android"] = "android"
    app_version: str | None = Field(default=None, max_length=40)


class PushTokenResponse(BaseModel):
    id: UUID
    platform: str
    app_version: str | None
    is_active: bool
    last_seen_at: datetime


class NotificationPreferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    in_app_enabled: bool = True
    push_enabled: bool = True
    email_enabled: bool = False
    muted_kinds: list[str] = Field(default_factory=list, max_length=100)
    quiet_hours_start: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class NotificationPreferenceResponse(BaseModel):
    in_app_enabled: bool
    push_enabled: bool
    email_enabled: bool
    muted_kinds: list[str]
    quiet_hours_start: str | None
    quiet_hours_end: str | None


def notification_deep_link(item: Notification) -> str:
    target_id = str(item.target_id) if item.target_id else ""
    routes = {
        "work_task": f"/app/tasks/{target_id}",
        "permission_request": f"/app/requests?permission={target_id}",
        "leave_request": f"/app/requests?leave={target_id}",
        "presence_request": f"/app/attendance?presence={target_id}",
        "geofence_exit_event": f"/app/attendance?geofence={target_id}",
        "employee_document": f"/app/requests?document={target_id}",
    }
    return routes.get(item.target_type or "", "/app")


def notification_response(item: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=item.id,
        kind=item.kind,
        title=item.title,
        body=item.body,
        actor_name=item.actor_name,
        target_type=item.target_type,
        target_id=item.target_id,
        urgent=item.urgent,
        read_at=item.read_at,
        created_at=item.created_at,
        deep_link=notification_deep_link(item),
    )


def leave_response(item: LeaveRequest) -> LeaveResponse:
    return LeaveResponse.model_validate(item, from_attributes=True)


def balance_response(item: LeaveBalance) -> LeaveBalanceResponse:
    return LeaveBalanceResponse(
        id=item.id,
        membership_id=item.membership_id,
        leave_type_id=item.leave_type_id,
        year=item.year,
        allocated_days=item.allocated_days,
        used_days=item.used_days,
        remaining_days=max(0, item.allocated_days - item.used_days),
        version=item.version,
    )


def document_status(item: EmployeeDocument, today: date | None = None) -> str:
    current = today or date.today()
    if item.review_status == "pending_review":
        return "pending_review"
    if item.expires_on is None:
        return "valid"
    if item.expires_on < current:
        return "expired"
    if item.expires_on <= current + timedelta(days=item.reminder_days):
        return "expiring_soon"
    return "valid"


def document_response(item: EmployeeDocument) -> DocumentResponse:
    return DocumentResponse(
        id=item.id,
        membership_id=item.membership_id,
        document_type=item.document_type,
        custom_type_name=item.custom_type_name,
        document_number=item.document_number,
        issued_on=item.issued_on,
        expires_on=item.expires_on,
        attachment_file_id=item.attachment_file_id,
        reminder_days=item.reminder_days,
        status=document_status(item),
        review_status=item.review_status,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def task_response(session: AsyncSession, task: WorkTask) -> TaskResponse:
    assignees = list(
        await session.scalars(
            select(TaskAssignee).where(
                TaskAssignee.company_id == task.company_id, TaskAssignee.task_id == task.id
            )
        )
    )
    extension = await session.scalar(
        select(TaskExtensionRequest)
        .where(
            TaskExtensionRequest.company_id == task.company_id,
            TaskExtensionRequest.task_id == task.id,
        )
        .order_by(TaskExtensionRequest.created_at.desc())
        .limit(1)
    )
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        due_at=task.due_at,
        status=task.status,
        created_by_membership_id=task.created_by_membership_id,
        assignee_ids=[item.membership_id for item in assignees],
        viewed_by_ids=[item.membership_id for item in assignees if item.viewed_at],
        completion_attachment_file_id=task.completion_attachment_file_id,
        latest_extension=(
            TaskExtensionResponse.model_validate(extension, from_attributes=True)
            if extension
            else None
        ),
        version=task.version,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def valid_member_ids(
    session: AsyncSession, company_id: UUID, requested: set[UUID]
) -> set[UUID]:
    if not requested:
        return set()
    return set(
        await session.scalars(
            select(CompanyMembership.id).where(
                CompanyMembership.company_id == company_id,
                CompanyMembership.id.in_(requested),
                CompanyMembership.status == "active",
            )
        )
    )


async def can_access_task(
    session: AsyncSession,
    company_id: UUID,
    membership_id: UUID,
    task_id: UUID,
    manager: bool,
    visible_members: frozenset[UUID] | None,
) -> WorkTask:
    criteria = [WorkTask.company_id == company_id, WorkTask.id == task_id]
    if not manager:
        criteria.append(
            or_(
                WorkTask.created_by_membership_id == membership_id,
                WorkTask.id.in_(
                    select(TaskAssignee.task_id).where(
                        TaskAssignee.company_id == company_id,
                        TaskAssignee.membership_id == membership_id,
                    )
                ),
            )
        )
    elif visible_members is not None:
        criteria.append(
            or_(
                WorkTask.created_by_membership_id == membership_id,
                WorkTask.id.in_(
                    select(TaskAssignee.task_id).where(
                        TaskAssignee.company_id == company_id,
                        TaskAssignee.membership_id.in_(visible_members),
                    )
                ),
            )
        )
    task = await session.scalar(select(WorkTask).where(*criteria))
    if task is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="task_not_found",
            title="Task not found",
            detail="The task is unavailable in the current company.",
        )
    return task


@tasks_router.get("/recipients", response_model=list[TaskRecipientResponse])
async def list_task_recipients(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> list[TaskRecipientResponse]:
    """Return people this user may address with a task."""
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.TASKS_VIEW)
    manager_roles = {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    is_manager = context.membership.role_code in manager_roles
    criteria = [
        CompanyMembership.company_id == context.company_id,
        CompanyMembership.status == "active",
        CompanyMembership.id != context.membership.id,
    ]
    if is_manager:
        criteria.append(CompanyMembership.role_code != "OWNER")
        visible = await visible_membership_ids(session, context)
        if visible is not None:
            criteria.append(CompanyMembership.id.in_(visible))
    else:
        criteria.append(CompanyMembership.role_code.in_(manager_roles))
    rows = await session.execute(
        select(
            CompanyMembership.id,
            CompanyMembership.role_code,
            User.email,
            EmployeeProfile.display_name,
        )
        .join(User, User.id == CompanyMembership.user_id)
        .outerjoin(
            EmployeeProfile,
            and_(
                EmployeeProfile.company_id == CompanyMembership.company_id,
                EmployeeProfile.membership_id == CompanyMembership.id,
            ),
        )
        .where(*criteria)
        .order_by(EmployeeProfile.display_name.asc().nullslast(), User.email.asc())
        .limit(500)
    )
    return [
        TaskRecipientResponse(
            id=membership_id,
            display_name=display_name or email,
            email=email,
            role_code=role_code,
        )
        for membership_id, role_code, email, display_name in rows
    ]


@tasks_router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    payload: TaskCreateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> TaskResponse:
    context = tenant_context(auth_session)
    manager_roles = {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    is_manager = context.membership.role_code in manager_roles
    await require_permission(
        session,
        context,
        Permission.TASKS_MANAGE if is_manager else Permission.TASKS_VIEW,
    )
    subscription = await active_subscription(session, context.company_id)
    if subscription is None or not bool(subscription[1].features.get("tasks", False)):
        raise ProblemError(
            status=403,
            code="subscription_feature_unavailable",
            title="Tasks are unavailable",
            detail="The current subscription does not include task management.",
        )
    target_ids = set(payload.membership_ids)
    if payload.branch_id:
        await require_branch_scope(session, context, payload.branch_id)
        target_ids.update(
            await session.scalars(
                select(EmployeeBranchAssignment.membership_id).where(
                    EmployeeBranchAssignment.company_id == context.company_id,
                    EmployeeBranchAssignment.branch_id == payload.branch_id,
                    EmployeeBranchAssignment.effective_to.is_(None),
                )
            )
        )
    if payload.group_id:
        await require_group_scope(session, context, payload.group_id)
        target_ids.update(
            await session.scalars(
                select(EmployeeGroupMembership.membership_id).where(
                    EmployeeGroupMembership.company_id == context.company_id,
                    EmployeeGroupMembership.group_id == payload.group_id,
                )
            )
        )
    if (
        not target_ids
        or await valid_member_ids(session, context.company_id, target_ids) != target_ids
    ):
        raise ProblemError(
            status=404,
            code="task_assignee_not_found",
            title="Task assignee not found",
            detail="Every assignee must be active in this company.",
        )
    if not is_manager:
        manager_ids = set(
            await session.scalars(
                select(CompanyMembership.id).where(
                    CompanyMembership.company_id == context.company_id,
                    CompanyMembership.status == "active",
                    CompanyMembership.role_code.in_(manager_roles),
                )
            )
        )
        if not target_ids.issubset(manager_ids):
            raise ProblemError(
                status=403,
                code="task_recipient_not_manager",
                title="Task recipient is not a manager",
                detail="Employees may send tasks only to a manager or company owner.",
            )
    visible = await visible_membership_ids(session, context) if is_manager else None
    if visible is not None and not target_ids.issubset(visible):
        raise ProblemError(
            status=404,
            code="task_assignee_not_found",
            title="Task assignee not found",
            detail="Every assignee must belong to the current access scope.",
        )
    task = WorkTask(
        company_id=context.company_id,
        created_by_membership_id=context.membership.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        priority=payload.priority,
        due_at=payload.due_at,
    )
    session.add(task)
    await session.flush()
    actor_name = await membership_actor_name(
        session, context.company_id, context.membership.id
    )
    session.add_all(
        [
            TaskAssignee(company_id=context.company_id, task_id=task.id, membership_id=member_id)
            for member_id in target_ids
        ]
        + [
            Notification(
                company_id=context.company_id,
                membership_id=member_id,
                kind="task_created",
                title=task.title,
                body="A new task was assigned to you.",
                actor_name=actor_name,
                target_type="work_task",
                target_id=task.id,
                urgent=task.priority == "urgent",
            )
            for member_id in target_ids
        ]
        + [
            TaskStatusHistory(
                company_id=context.company_id,
                task_id=task.id,
                changed_by_membership_id=context.membership.id,
                old_status=None,
                new_status="new",
            )
        ]
    )
    await session.commit()
    await session.refresh(task)
    return await task_response(session, task)


@tasks_router.get("", response_model=list[TaskResponse])
async def list_tasks(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    task_status: Annotated[str | None, Query(alias="status")] = None,
    mine: bool = False,
) -> list[TaskResponse]:
    context = tenant_context(auth_session)
    criteria = [WorkTask.company_id == context.company_id]
    is_manager = context.membership.role_code in {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    if mine or not is_manager:
        criteria.append(
            WorkTask.id.in_(
                select(TaskAssignee.task_id).where(
                    TaskAssignee.company_id == context.company_id,
                    TaskAssignee.membership_id == context.membership.id,
                )
            )
        )
    else:
        await require_permission(session, context, Permission.TASKS_VIEW)
        visible = await visible_membership_ids(session, context)
        if visible is not None:
            criteria.append(
                or_(
                    WorkTask.created_by_membership_id == context.membership.id,
                    WorkTask.id.in_(
                        select(TaskAssignee.task_id).where(
                            TaskAssignee.company_id == context.company_id,
                            TaskAssignee.membership_id.in_(visible),
                        )
                    ),
                )
            )
    if task_status:
        if task_status not in TASK_STATUSES:
            raise ProblemError(
                status=422,
                code="task_status_invalid",
                title="Invalid task status",
                detail="Use a supported task status.",
            )
        criteria.append(WorkTask.status == task_status)
    tasks = list(
        await session.scalars(
            select(WorkTask)
            .where(*criteria)
            .order_by(WorkTask.due_at.asc().nullslast(), WorkTask.created_at.desc())
            .limit(1000)
        )
    )
    return [await task_response(session, task) for task in tasks]


@tasks_router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID, auth_session: CurrentAuthSession, session: DatabaseSession
) -> TaskResponse:
    context = tenant_context(auth_session)
    is_manager = context.membership.role_code in {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    visible = await visible_membership_ids(session, context) if is_manager else None
    task = await can_access_task(
        session, context.company_id, context.membership.id, task_id, is_manager, visible
    )
    assignee = await session.scalar(
        select(TaskAssignee)
        .where(
            TaskAssignee.company_id == context.company_id,
            TaskAssignee.task_id == task.id,
            TaskAssignee.membership_id == context.membership.id,
        )
        .with_for_update()
    )
    if assignee and assignee.viewed_at is None:
        assignee.viewed_at = datetime.now(UTC)
        if task.status == "new":
            task.status = "viewed"
            task.version += 1
        await session.commit()
    return await task_response(session, task)


@tasks_router.post("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: UUID,
    payload: TaskUpdateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> TaskResponse:
    context = tenant_context(auth_session)
    is_manager = context.membership.role_code in {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    visible = await visible_membership_ids(session, context) if is_manager else None
    task = await can_access_task(
        session, context.company_id, context.membership.id, task_id, is_manager, visible
    )
    if task.version != payload.version:
        raise ProblemError(
            status=409,
            code="concurrency_conflict",
            title="Task changed",
            detail="Reload the task before saving again.",
        )
    if payload.status == "needs_more_time":
        is_assignee = await session.scalar(
            select(TaskAssignee.id).where(
                TaskAssignee.company_id == context.company_id,
                TaskAssignee.task_id == task.id,
                TaskAssignee.membership_id == context.membership.id,
            )
        )
        if is_assignee is None:
            raise ProblemError(
                status=403,
                code="task_extension_assignee_required",
                title="Task assignee required",
                detail="Only an assigned employee can request more time.",
            )
        pending_extension = await session.scalar(
            select(TaskExtensionRequest.id).where(
                TaskExtensionRequest.company_id == context.company_id,
                TaskExtensionRequest.task_id == task.id,
                TaskExtensionRequest.status == "pending",
            )
        )
        if pending_extension is not None:
            raise ProblemError(
                status=409,
                code="task_extension_pending",
                title="Task extension already pending",
                detail="The manager must decide the current extension request first.",
            )
        session.add(
            TaskExtensionRequest(
                company_id=context.company_id,
                task_id=task.id,
                requested_by_membership_id=context.membership.id,
                reason=payload.reason or "",
                requested_due_at=payload.requested_due_at,
            )
        )
    old_status = task.status
    await require_owned_attachment(session, context, payload.completion_attachment_file_id)
    task.status = payload.status
    task.completion_attachment_file_id = payload.completion_attachment_file_id
    task.version += 1
    session.add(
        TaskStatusHistory(
            company_id=context.company_id,
            task_id=task.id,
            changed_by_membership_id=context.membership.id,
            old_status=old_status,
            new_status=task.status,
            reason=payload.reason,
        )
    )
    if context.membership.id != task.created_by_membership_id:
        actor_name = await membership_actor_name(
            session, context.company_id, context.membership.id
        )
        completed_with_attachment = (
            payload.status == "completed"
            and payload.completion_attachment_file_id is not None
        )
        session.add(
            Notification(
                company_id=context.company_id,
                membership_id=task.created_by_membership_id,
                kind="task_completed" if payload.status == "completed" else "task_status_changed",
                title=task.title,
                actor_name=actor_name,
                body=(
                    "The task was completed and a receipt was attached."
                    if completed_with_attachment
                    else (
                        "The task was completed."
                        if payload.status == "completed"
                        else f"Task status changed to {task.status}."
                    )
                ),
                target_type="work_task",
                target_id=task.id,
            )
        )
    await session.commit()
    await session.refresh(task)
    return await task_response(session, task)


@tasks_router.post("/{task_id}/extension-decision", response_model=TaskResponse)
async def decide_task_extension(
    task_id: UUID,
    payload: TaskExtensionDecisionRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> TaskResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.TASKS_MANAGE)
    visible = await visible_membership_ids(session, context)
    task = await can_access_task(
        session, context.company_id, context.membership.id, task_id, True, visible
    )
    if task.version != payload.version:
        raise ProblemError(
            status=409,
            code="concurrency_conflict",
            title="Task changed",
            detail="Reload the task before deciding the extension request.",
        )
    extension = await session.scalar(
        select(TaskExtensionRequest)
        .where(
            TaskExtensionRequest.company_id == context.company_id,
            TaskExtensionRequest.task_id == task.id,
            TaskExtensionRequest.status == "pending",
        )
        .with_for_update()
    )
    if extension is None:
        raise ProblemError(
            status=409,
            code="task_extension_not_pending",
            title="No pending task extension",
            detail="This task has no pending extension request.",
        )
    now = datetime.now(UTC)
    actor_name = await membership_actor_name(
        session, context.company_id, context.membership.id
    )
    old_status = task.status
    extension.status = payload.decision
    extension.decided_by_membership_id = context.membership.id
    extension.decision_comment = payload.comment
    extension.decided_at = now
    extension.approved_due_at = payload.new_due_at if payload.decision == "approved" else None
    if payload.decision == "approved":
        task.due_at = payload.new_due_at
    task.status = "in_progress"
    task.version += 1
    session.add(
        TaskStatusHistory(
            company_id=context.company_id,
            task_id=task.id,
            changed_by_membership_id=context.membership.id,
            old_status=old_status,
            new_status=task.status,
            reason=f"Extension {payload.decision}: {payload.comment}",
        )
    )
    session.add(
        Notification(
            company_id=context.company_id,
            membership_id=extension.requested_by_membership_id,
            kind=f"task_extension_{payload.decision}",
            title=task.title,
            actor_name=actor_name,
            body=(
                "The task extension was approved."
                if payload.decision == "approved"
                else "The task extension was rejected."
            ),
            target_type="work_task",
            target_id=task.id,
        )
    )
    await session.commit()
    await session.refresh(task)
    return await task_response(session, task)


@tasks_router.patch("/{task_id}", response_model=TaskResponse)
async def manager_update_task(
    task_id: UUID,
    payload: TaskManagerUpdateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> TaskResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.TASKS_MANAGE)
    visible = await visible_membership_ids(session, context)
    task = await can_access_task(
        session, context.company_id, context.membership.id, task_id, True, visible
    )
    if task.version != payload.version:
        raise ProblemError(
            status=409,
            code="concurrency_conflict",
            title="Task changed",
            detail="Reload the task before saving again.",
        )
    if "due_at" in payload.model_fields_set:
        task.due_at = payload.due_at
    if payload.membership_ids is not None:
        requested = set(payload.membership_ids)
        if (
            not requested
            or await valid_member_ids(session, context.company_id, requested) != requested
        ):
            raise ProblemError(
                status=404,
                code="task_assignee_not_found",
                title="Task assignee not found",
                detail="Every assignee must be active in this company.",
            )
        if visible is not None and not requested.issubset(visible):
            raise ProblemError(
                status=404,
                code="task_assignee_not_found",
                title="Task assignee not found",
                detail="Every assignee must belong to the current access scope.",
            )
        existing = list(
            await session.scalars(
                select(TaskAssignee).where(
                    TaskAssignee.company_id == context.company_id, TaskAssignee.task_id == task.id
                )
            )
        )
        existing_ids = {item.membership_id for item in existing}
        for item in existing:
            if item.membership_id not in requested:
                await session.delete(item)
        session.add_all(
            [
                TaskAssignee(
                    company_id=context.company_id, task_id=task.id, membership_id=member_id
                )
                for member_id in requested - existing_ids
            ]
        )
    task.version += 1
    await session.commit()
    await session.refresh(task)
    return await task_response(session, task)


@tasks_router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=201)
async def add_task_comment(
    task_id: UUID,
    payload: TaskCommentRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> TaskCommentResponse:
    context = tenant_context(auth_session)
    is_manager = context.membership.role_code in {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    visible = await visible_membership_ids(session, context) if is_manager else None
    task = await can_access_task(
        session, context.company_id, context.membership.id, task_id, is_manager, visible
    )
    await require_owned_attachment(session, context, payload.attachment_file_id)
    comment = TaskComment(
        company_id=context.company_id,
        task_id=task.id,
        author_membership_id=context.membership.id,
        **payload.model_dump(),
    )
    session.add(comment)
    assignee_ids = set(
        await session.scalars(
            select(TaskAssignee.membership_id).where(
                TaskAssignee.company_id == context.company_id,
                TaskAssignee.task_id == task.id,
            )
        )
    )
    notification_recipient_ids = {
        task.created_by_membership_id,
        *assignee_ids,
    } - {context.membership.id}
    actor_name = await membership_actor_name(
        session, context.company_id, context.membership.id
    )
    session.add_all(
        [
            Notification(
                company_id=context.company_id,
                membership_id=membership_id,
                kind="task_comment_added",
                title=task.title,
                body="A new message was added to a task.",
                actor_name=actor_name,
                target_type="work_task",
                target_id=task.id,
            )
            for membership_id in notification_recipient_ids
        ]
    )
    await session.commit()
    await session.refresh(comment)
    return TaskCommentResponse.model_validate(comment, from_attributes=True)


@tasks_router.get("/{task_id}/comments", response_model=list[TaskCommentResponse])
async def list_task_comments(
    task_id: UUID, auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[TaskCommentResponse]:
    context = tenant_context(auth_session)
    is_manager = context.membership.role_code in {"OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR"}
    visible = await visible_membership_ids(session, context) if is_manager else None
    await can_access_task(
        session, context.company_id, context.membership.id, task_id, is_manager, visible
    )
    items = await session.scalars(
        select(TaskComment)
        .where(TaskComment.company_id == context.company_id, TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.asc())
    )
    return [TaskCommentResponse.model_validate(item, from_attributes=True) for item in items]


@leave_router.post("/types", response_model=LeaveTypeResponse, status_code=201)
async def create_leave_type(
    payload: LeaveTypeRequest, auth_session: CurrentAuthSession, session: DatabaseSession
) -> LeaveTypeResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.LEAVE_MANAGE)
    await require_unrestricted_scope(session, context)
    item = LeaveType(
        company_id=context.company_id,
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        default_days=payload.default_days,
        is_paid=payload.is_paid,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return LeaveTypeResponse.model_validate(item, from_attributes=True)


@leave_router.get("/types", response_model=list[LeaveTypeResponse])
async def list_leave_types(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[LeaveTypeResponse]:
    context = tenant_context(auth_session)
    items = await session.scalars(
        select(LeaveType)
        .where(LeaveType.company_id == context.company_id, LeaveType.is_active.is_(True))
        .order_by(LeaveType.name.asc())
    )
    return [LeaveTypeResponse.model_validate(item, from_attributes=True) for item in items]


@leave_router.put("/balances", response_model=LeaveBalanceResponse)
async def set_leave_balance(
    payload: LeaveBalanceRequest, auth_session: CurrentAuthSession, session: DatabaseSession
) -> LeaveBalanceResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.LEAVE_MANAGE)
    await require_membership_scope(session, context, payload.membership_id)
    member = await valid_member_ids(session, context.company_id, {payload.membership_id})
    leave_type = await session.scalar(
        select(LeaveType.id).where(
            LeaveType.company_id == context.company_id, LeaveType.id == payload.leave_type_id
        )
    )
    if not member or leave_type is None:
        raise ProblemError(
            status=404,
            code="leave_balance_target_not_found",
            title="Leave balance target not found",
            detail="The employee or leave type was not found in this company.",
        )
    item = await session.scalar(
        select(LeaveBalance)
        .where(
            LeaveBalance.company_id == context.company_id,
            LeaveBalance.membership_id == payload.membership_id,
            LeaveBalance.leave_type_id == payload.leave_type_id,
            LeaveBalance.year == payload.year,
        )
        .with_for_update()
    )
    old_allocation = item.allocated_days if item else 0
    if item is None:
        item = LeaveBalance(
            company_id=context.company_id,
            membership_id=payload.membership_id,
            leave_type_id=payload.leave_type_id,
            year=payload.year,
            allocated_days=payload.allocated_days,
        )
        session.add(item)
    else:
        if payload.allocated_days < item.used_days:
            raise ProblemError(
                status=409,
                code="leave_balance_below_used",
                title="Invalid leave allocation",
                detail="Allocated days cannot be lower than already used days.",
            )
        item.allocated_days = payload.allocated_days
        item.version += 1
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="leave.balance_updated",
            target_type="leave_balance",
            target_id=item.id,
            details={
                "reason": payload.reason,
                "old": old_allocation,
                "new": payload.allocated_days,
            },
        )
    )
    await session.commit()
    await session.refresh(item)
    return balance_response(item)


@leave_router.get("/balances", response_model=list[LeaveBalanceResponse])
async def list_leave_balances(
    auth_session: CurrentAuthSession, session: DatabaseSession, membership_id: UUID | None = None
) -> list[LeaveBalanceResponse]:
    context = tenant_context(auth_session)
    target = membership_id or context.membership.id
    if target != context.membership.id:
        await require_permission(session, context, Permission.LEAVE_VIEW)
        await require_membership_scope(session, context, target)
    items = await session.scalars(
        select(LeaveBalance)
        .where(LeaveBalance.company_id == context.company_id, LeaveBalance.membership_id == target)
        .order_by(LeaveBalance.year.desc())
    )
    return [balance_response(item) for item in items]


@leave_router.post("/requests", response_model=LeaveResponse, status_code=201)
async def create_leave_request(
    payload: LeaveCreateRequest, auth_session: CurrentAuthSession, session: DatabaseSession
) -> LeaveResponse:
    context = tenant_context(auth_session)
    leave_type = await session.scalar(
        select(LeaveType.id).where(
            LeaveType.company_id == context.company_id,
            LeaveType.id == payload.leave_type_id,
            LeaveType.is_active.is_(True),
        )
    )
    if leave_type is None:
        raise ProblemError(
            status=404,
            code="leave_type_not_found",
            title="Leave type not found",
            detail="Select an active leave type from this company.",
        )
    overlap = await session.scalar(
        select(LeaveRequest.id).where(
            LeaveRequest.company_id == context.company_id,
            LeaveRequest.membership_id == context.membership.id,
            LeaveRequest.status.in_(("pending", "approved")),
            LeaveRequest.starts_on <= payload.ends_on,
            LeaveRequest.ends_on >= payload.starts_on,
        )
    )
    if overlap:
        raise ProblemError(
            status=409,
            code="leave_request_overlap",
            title="Leave request overlaps",
            detail="An active leave request already covers part of this period.",
        )
    days = (payload.ends_on - payload.starts_on).days + 1
    await require_owned_attachment(session, context, payload.attachment_file_id)
    item = LeaveRequest(
        company_id=context.company_id,
        membership_id=context.membership.id,
        days=days,
        **payload.model_dump(),
    )
    session.add(item)
    await session.flush()
    manager_ids = await session.scalars(
        select(CompanyMembership.id).where(
            CompanyMembership.company_id == context.company_id,
            CompanyMembership.status == "active",
            CompanyMembership.role_code.in_(("OWNER", "MANAGER", "HR_OFFICER")),
        )
    )
    actor_name = await membership_actor_name(
        session, context.company_id, context.membership.id
    )
    session.add_all(
        [
            Notification(
                company_id=context.company_id,
                membership_id=manager_id,
                kind="leave_requested",
                title="Leave request",
                body="An employee submitted a leave request.",
                actor_name=actor_name,
                target_type="leave_request",
                target_id=item.id,
            )
            for manager_id in manager_ids
        ]
    )
    await session.commit()
    await session.refresh(item)
    return leave_response(item)


@leave_router.get("/requests", response_model=list[LeaveResponse])
async def list_leave_requests(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    mine: bool = False,
    request_status: Annotated[str | None, Query(alias="status")] = None,
) -> list[LeaveResponse]:
    context = tenant_context(auth_session)
    criteria = [LeaveRequest.company_id == context.company_id]
    if mine or context.membership.role_code == "EMPLOYEE":
        criteria.append(LeaveRequest.membership_id == context.membership.id)
    else:
        await require_permission(session, context, Permission.LEAVE_VIEW)
        visible = await visible_membership_ids(session, context)
        if visible is not None:
            criteria.append(LeaveRequest.membership_id.in_(visible))
    if request_status:
        criteria.append(LeaveRequest.status == request_status)
    items = await session.scalars(
        select(LeaveRequest).where(*criteria).order_by(LeaveRequest.created_at.desc()).limit(1000)
    )
    return [leave_response(item) for item in items]


@leave_router.post("/requests/{request_id}/review", response_model=LeaveResponse)
async def review_leave_request(
    request_id: UUID,
    payload: LeaveReviewRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey = None,
) -> LeaveResponse:
    context = tenant_context(auth_session)
    idempotency, replay = await begin_idempotency(
        session, context, f"leave.review:{request_id}", idempotency_key, payload
    )
    if replay is not None:
        return LeaveResponse.model_validate(replay)
    await require_permission(session, context, Permission.LEAVE_MANAGE)
    item = await session.scalar(
        select(LeaveRequest)
        .where(
            LeaveRequest.company_id == context.company_id,
            LeaveRequest.id == request_id,
            LeaveRequest.status == "pending",
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="leave_request_not_found",
            title="Leave request not found",
            detail="A pending request was not found in this company.",
        )
    await require_membership_scope(session, context, item.membership_id)
    if payload.decision == "approved":
        balance = await session.scalar(
            select(LeaveBalance)
            .where(
                LeaveBalance.company_id == context.company_id,
                LeaveBalance.membership_id == item.membership_id,
                LeaveBalance.leave_type_id == item.leave_type_id,
                LeaveBalance.year == item.starts_on.year,
            )
            .with_for_update()
        )
        if balance is None or balance.allocated_days - balance.used_days < item.days:
            raise ProblemError(
                status=409,
                code="leave_balance_insufficient",
                title="Insufficient leave balance",
                detail="The employee does not have enough remaining leave days.",
            )
        balance.used_days += item.days
        balance.version += 1
        records = await session.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.company_id == context.company_id,
                AttendanceRecord.membership_id == item.membership_id,
                AttendanceRecord.work_date >= item.starts_on,
                AttendanceRecord.work_date <= item.ends_on,
            )
        )
        for record in records:
            if record.checked_in_at is None:
                record.status = "on_leave"
    item.status = payload.decision
    item.reviewed_by_membership_id = context.membership.id
    item.review_comment = payload.comment
    item.reviewed_at = datetime.now(UTC)
    actor_name = await membership_actor_name(
        session, context.company_id, context.membership.id
    )
    session.add_all(
        [
            Notification(
                company_id=context.company_id,
                membership_id=item.membership_id,
                kind="leave_reviewed",
                title="Leave request reviewed",
                body=f"Your leave request was {payload.decision}.",
                actor_name=actor_name,
                target_type="leave_request",
                target_id=item.id,
            ),
            AuditLog(
                company_id=context.company_id,
                actor_membership_id=context.membership.id,
                action=f"leave.{payload.decision}",
                target_type="leave_request",
                target_id=item.id,
                details={"comment": payload.comment or "", "days": item.days},
            ),
        ]
    )
    result = leave_response(item)
    complete_idempotency(idempotency, result, status.HTTP_200_OK)
    await session.commit()
    return result


@documents_router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    payload: DocumentCreateRequest, auth_session: CurrentAuthSession, session: DatabaseSession
) -> DocumentResponse:
    context = tenant_context(auth_session)
    subscription = await active_subscription(session, context.company_id)
    if subscription is None or not bool(subscription[1].features.get("documents", False)):
        raise ProblemError(
            status=403,
            code="subscription_feature_unavailable",
            title="Documents are unavailable",
            detail="The current subscription does not include employee documents.",
        )
    target = payload.membership_id or context.membership.id
    if target != context.membership.id:
        await require_permission(session, context, Permission.DOCUMENTS_MANAGE)
        await require_membership_scope(session, context, target)
    if not await valid_member_ids(session, context.company_id, {target}):
        raise ProblemError(
            status=404,
            code="document_employee_not_found",
            title="Employee not found",
            detail="The employee was not found in this company.",
        )
    await require_owned_attachment(session, context, payload.attachment_file_id)
    values = payload.model_dump(exclude={"membership_id"})
    item = EmployeeDocument(company_id=context.company_id, membership_id=target, **values)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return document_response(item)


@documents_router.get("", response_model=list[DocumentResponse])
async def list_documents(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    membership_id: UUID | None = None,
    expiring_within_days: Annotated[int | None, Query(ge=0, le=365)] = None,
) -> list[DocumentResponse]:
    context = tenant_context(auth_session)
    can_view_all = context.membership.role_code in {"OWNER", "MANAGER", "HR_OFFICER"}
    target = membership_id or (None if can_view_all else context.membership.id)
    if target is not None and target != context.membership.id:
        await require_permission(session, context, Permission.DOCUMENTS_VIEW)
        await require_membership_scope(session, context, target)
    criteria = [EmployeeDocument.company_id == context.company_id]
    if target is not None:
        criteria.append(EmployeeDocument.membership_id == target)
    elif can_view_all:
        visible = await visible_membership_ids(session, context)
        if visible is not None:
            criteria.append(EmployeeDocument.membership_id.in_(visible))
    if expiring_within_days is not None:
        criteria.extend(
            [
                EmployeeDocument.expires_on.is_not(None),
                EmployeeDocument.expires_on <= date.today() + timedelta(days=expiring_within_days),
            ]
        )
    items = await session.scalars(
        select(EmployeeDocument)
        .where(*criteria)
        .order_by(EmployeeDocument.expires_on.asc().nullslast())
    )
    return [document_response(item) for item in items]


@documents_router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DocumentResponse:
    context = tenant_context(auth_session)
    item = await session.scalar(
        select(EmployeeDocument).where(
            EmployeeDocument.company_id == context.company_id,
            EmployeeDocument.id == document_id,
        )
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="document_not_found",
            title="Document not found",
            detail="The document was not found in this company.",
        )
    if item.membership_id != context.membership.id:
        await require_permission(session, context, Permission.DOCUMENTS_VIEW)
        await require_membership_scope(session, context, item.membership_id)
    return document_response(item)


@documents_router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    payload: DocumentUpdateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DocumentResponse:
    context = tenant_context(auth_session)
    item = await session.scalar(
        select(EmployeeDocument)
        .where(
            EmployeeDocument.company_id == context.company_id,
            EmployeeDocument.id == document_id,
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="document_not_found",
            title="Document not found",
            detail="The document was not found in this company.",
        )
    if item.membership_id != context.membership.id:
        await require_permission(session, context, Permission.DOCUMENTS_MANAGE)
        await require_membership_scope(session, context, item.membership_id)
    if item.version != payload.version:
        raise ProblemError(
            status=409,
            code="concurrency_conflict",
            title="Document changed",
            detail="Reload the document before updating it.",
        )
    if payload.attachment_file_id != item.attachment_file_id:
        await require_owned_attachment(session, context, payload.attachment_file_id)
    values = payload.model_dump(exclude={"version"})
    changed_fields = [key for key, value in values.items() if getattr(item, key) != value]
    for key, value in values.items():
        setattr(item, key, value)
    if changed_fields:
        item.review_status = "pending_review"
    item.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="document.updated",
            target_type="employee_document",
            target_id=item.id,
            details={"changed_fields": sorted(changed_fields)},
        )
    )
    await session.commit()
    await session.refresh(item)
    return document_response(item)


@documents_router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    version: Annotated[int, Query(ge=1)],
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> None:
    context = tenant_context(auth_session)
    item = await session.scalar(
        select(EmployeeDocument)
        .where(
            EmployeeDocument.company_id == context.company_id,
            EmployeeDocument.id == document_id,
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="document_not_found",
            title="Document not found",
            detail="The document was not found in this company.",
        )
    if item.membership_id != context.membership.id:
        await require_permission(session, context, Permission.DOCUMENTS_MANAGE)
        await require_membership_scope(session, context, item.membership_id)
    if item.version != version:
        raise ProblemError(
            status=409,
            code="concurrency_conflict",
            title="Document changed",
            detail="Reload the document before deleting it.",
        )
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="document.deleted",
            target_type="employee_document",
            target_id=item.id,
            details={"document_type": item.document_type},
        )
    )
    await session.delete(item)
    await session.commit()


@documents_router.post("/{document_id}/review", response_model=DocumentResponse)
async def review_document(
    document_id: UUID,
    payload: DocumentReviewRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DocumentResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DOCUMENTS_MANAGE)
    item = await session.scalar(
        select(EmployeeDocument)
        .where(
            EmployeeDocument.company_id == context.company_id, EmployeeDocument.id == document_id
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="document_not_found",
            title="Document not found",
            detail="The document was not found in this company.",
        )
    await require_membership_scope(session, context, item.membership_id)
    item.review_status = payload.decision
    item.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="document.reviewed",
            target_type="employee_document",
            target_id=item.id,
            details={"decision": payload.decision},
        )
    )
    await session.commit()
    await session.refresh(item)
    return document_response(item)


@notifications_router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    auth_session: CurrentAuthSession, session: DatabaseSession, unread_only: bool = False
) -> list[NotificationResponse]:
    context = tenant_context(auth_session)
    criteria = [
        Notification.company_id == context.company_id,
        Notification.membership_id == context.membership.id,
    ]
    if unread_only:
        criteria.append(Notification.read_at.is_(None))
    items = await session.scalars(
        select(Notification).where(*criteria).order_by(Notification.created_at.desc()).limit(500)
    )
    return [notification_response(item) for item in items]


@notifications_router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_notification_count(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> UnreadCountResponse:
    context = tenant_context(auth_session)
    count = int(
        await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.company_id == context.company_id,
                Notification.membership_id == context.membership.id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )
    return UnreadCountResponse(unread_count=count)


@notifications_router.get("/provider-status", response_model=PushProviderResponse)
async def push_provider_status(auth_session: CurrentAuthSession) -> PushProviderResponse:
    tenant_context(auth_session)
    return PushProviderResponse(configured=FirebasePushAdapter().configured)


@notifications_router.post("/read-all", response_model=UnreadCountResponse)
async def mark_all_notifications_read(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> UnreadCountResponse:
    context = tenant_context(auth_session)
    await session.execute(
        update(Notification)
        .where(
            Notification.company_id == context.company_id,
            Notification.membership_id == context.membership.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    await session.commit()
    return UnreadCountResponse(unread_count=0)


@notifications_router.post("/push-tokens", response_model=PushTokenResponse)
async def register_push_token(
    payload: PushTokenRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> PushTokenResponse:
    context = tenant_context(auth_session)
    token_hash = sha256(payload.token.encode("utf-8")).hexdigest()
    item = await session.scalar(
        select(PushDeviceToken).where(PushDeviceToken.token_hash == token_hash).with_for_update()
    )
    if item is not None and (
        item.company_id != context.company_id or item.membership_id != context.membership.id
    ):
        # One device can sign in as different users. Keep historical delivery
        # rows attached to the former owner, but revoke that token before
        # registering it for the currently authenticated membership.
        item.is_active = False
        item.token = ""
        item.token_hash = sha256(f"revoked:{item.id}".encode("utf-8")).hexdigest()
        await session.flush()
        item = None
    if item is None:
        item = PushDeviceToken(
            company_id=context.company_id,
            membership_id=context.membership.id,
            token=payload.token,
            token_hash=token_hash,
            platform=payload.platform,
            app_version=payload.app_version,
        )
        session.add(item)
    else:
        item.token = payload.token
        item.platform = payload.platform
        item.app_version = payload.app_version
        item.is_active = True
        item.last_seen_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(item)
    return PushTokenResponse.model_validate(item, from_attributes=True)


@notifications_router.delete("/push-tokens/{token_id}", status_code=204)
async def unregister_push_token(
    token_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> None:
    context = tenant_context(auth_session)
    item = await session.scalar(
        select(PushDeviceToken)
        .where(
            PushDeviceToken.company_id == context.company_id,
            PushDeviceToken.membership_id == context.membership.id,
            PushDeviceToken.id == token_id,
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="push_token_not_found",
            title="Push token not found",
            detail="The push token does not belong to this member.",
        )
    item.is_active = False
    await session.commit()


@notifications_router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> NotificationPreferenceResponse:
    context = tenant_context(auth_session)
    item = await session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.company_id == context.company_id,
            NotificationPreference.membership_id == context.membership.id,
        )
    )
    if item is None:
        return NotificationPreferenceResponse(
            in_app_enabled=True,
            push_enabled=True,
            email_enabled=False,
            muted_kinds=[],
            quiet_hours_start=None,
            quiet_hours_end=None,
        )
    return NotificationPreferenceResponse.model_validate(item, from_attributes=True)


@notifications_router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    payload: NotificationPreferenceRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> NotificationPreferenceResponse:
    context = tenant_context(auth_session)
    item = await session.scalar(
        select(NotificationPreference)
        .where(
            NotificationPreference.company_id == context.company_id,
            NotificationPreference.membership_id == context.membership.id,
        )
        .with_for_update()
    )
    values = payload.model_dump()
    values["muted_kinds"] = sorted(set(payload.muted_kinds))
    if item is None:
        item = NotificationPreference(
            company_id=context.company_id,
            membership_id=context.membership.id,
            **values,
        )
        session.add(item)
    else:
        for key, value in values.items():
            setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return NotificationPreferenceResponse.model_validate(item, from_attributes=True)


@notifications_router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID, auth_session: CurrentAuthSession, session: DatabaseSession
) -> NotificationResponse:
    context = tenant_context(auth_session)
    item = await session.scalar(
        select(Notification)
        .where(
            Notification.company_id == context.company_id,
            Notification.membership_id == context.membership.id,
            Notification.id == notification_id,
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="notification_not_found",
            title="Notification not found",
            detail="The notification does not exist for this employee.",
        )
    item.read_at = item.read_at or datetime.now(UTC)
    await session.commit()
    await session.refresh(item)
    return notification_response(item)
