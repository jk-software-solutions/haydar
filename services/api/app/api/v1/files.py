from hashlib import sha256
from typing import Annotated, Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    effective_permission_codes,
    tenant_context,
    visible_membership_ids,
)
from app.core.errors import ProblemError
from app.core.subscription_catalog import active_subscription, plan_limit
from app.db.session import get_session
from app.models.attendance import AttendanceEvent, AttendanceRecord, PermissionRequest
from app.models.files import StoredFile
from app.models.identity import Company
from app.models.workforce import (
    EmployeeDocument,
    LeaveRequest,
    TaskAssignee,
    TaskComment,
    WorkTask,
)
from app.models.organization import EmployeeProfile

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # Task conversations may include voice notes and other audio evidence.
    "audio/aac",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/3gpp",
    "application/ogg",
}
MAX_FILE_BYTES = 10 * 1024 * 1024
VIDEO_EXTENSIONS = {
    ".3g2",
    ".3gp",
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
}


class FileResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


async def can_download_linked_file(
    session: AsyncSession,
    auth_session: CurrentAuthSession,
    file_id: UUID,
) -> bool:
    context = tenant_context(auth_session)
    member_id = context.membership.id
    personal_references = (
        select(Company.id).where(
            Company.id == context.company_id,
            Company.logo_file_id == file_id,
        ),
        select(PermissionRequest.id).where(
            PermissionRequest.company_id == context.company_id,
            PermissionRequest.membership_id == member_id,
            PermissionRequest.attachment_file_id == file_id,
        ),
        select(LeaveRequest.id).where(
            LeaveRequest.company_id == context.company_id,
            LeaveRequest.membership_id == member_id,
            LeaveRequest.attachment_file_id == file_id,
        ),
        select(EmployeeDocument.id).where(
            EmployeeDocument.company_id == context.company_id,
            EmployeeDocument.membership_id == member_id,
            EmployeeDocument.attachment_file_id == file_id,
        ),
        select(EmployeeProfile.id).where(
            EmployeeProfile.company_id == context.company_id,
            EmployeeProfile.membership_id == member_id,
            EmployeeProfile.avatar_file_id == file_id,
        ),
        select(AttendanceEvent.id)
        .join(
            AttendanceRecord,
            (AttendanceRecord.company_id == AttendanceEvent.company_id)
            & (AttendanceRecord.id == AttendanceEvent.record_id),
        )
        .where(
            AttendanceEvent.company_id == context.company_id,
            AttendanceEvent.attachment_file_id == file_id,
            AttendanceRecord.membership_id == member_id,
        ),
        select(WorkTask.id)
        .outerjoin(
            TaskAssignee,
            (TaskAssignee.company_id == WorkTask.company_id)
            & (TaskAssignee.task_id == WorkTask.id),
        )
        .where(
            WorkTask.company_id == context.company_id,
            WorkTask.completion_attachment_file_id == file_id,
            or_(
                WorkTask.created_by_membership_id == member_id,
                TaskAssignee.membership_id == member_id,
            ),
        ),
        select(TaskComment.id)
        .join(
            WorkTask,
            (WorkTask.company_id == TaskComment.company_id) & (WorkTask.id == TaskComment.task_id),
        )
        .outerjoin(
            TaskAssignee,
            (TaskAssignee.company_id == WorkTask.company_id)
            & (TaskAssignee.task_id == WorkTask.id),
        )
        .where(
            TaskComment.company_id == context.company_id,
            TaskComment.attachment_file_id == file_id,
            or_(
                WorkTask.created_by_membership_id == member_id,
                TaskAssignee.membership_id == member_id,
            ),
        ),
    )
    for query in personal_references:
        if await session.scalar(query.limit(1)) is not None:
            return True

    permissions = await effective_permission_codes(
        session, context.company_id, context.membership.id
    )
    visible = await visible_membership_ids(session, context)
    scoped_members = visible if visible is not None else None

    async def referenced_for_members(query: Any) -> bool:
        return await session.scalar(query.limit(1)) is not None

    if Permission.PERMISSIONS_VIEW.value in permissions:
        query = select(PermissionRequest.id).where(
            PermissionRequest.company_id == context.company_id,
            PermissionRequest.attachment_file_id == file_id,
        )
        if scoped_members is not None:
            query = query.where(PermissionRequest.membership_id.in_(scoped_members))
        if await referenced_for_members(query):
            return True
    if Permission.MEMBERS_VIEW.value in permissions:
        query = select(EmployeeProfile.id).where(
            EmployeeProfile.company_id == context.company_id,
            EmployeeProfile.avatar_file_id == file_id,
        )
        if scoped_members is not None:
            query = query.where(EmployeeProfile.membership_id.in_(scoped_members))
        if await referenced_for_members(query):
            return True
    if Permission.LEAVE_VIEW.value in permissions:
        query = select(LeaveRequest.id).where(
            LeaveRequest.company_id == context.company_id,
            LeaveRequest.attachment_file_id == file_id,
        )
        if scoped_members is not None:
            query = query.where(LeaveRequest.membership_id.in_(scoped_members))
        if await referenced_for_members(query):
            return True
    if Permission.DOCUMENTS_VIEW.value in permissions:
        query = select(EmployeeDocument.id).where(
            EmployeeDocument.company_id == context.company_id,
            EmployeeDocument.attachment_file_id == file_id,
        )
        if scoped_members is not None:
            query = query.where(EmployeeDocument.membership_id.in_(scoped_members))
        if await referenced_for_members(query):
            return True
    if Permission.ATTENDANCE_VIEW.value in permissions:
        query = (
            select(AttendanceEvent.id)
            .join(
                AttendanceRecord,
                (AttendanceRecord.company_id == AttendanceEvent.company_id)
                & (AttendanceRecord.id == AttendanceEvent.record_id),
            )
            .where(
                AttendanceEvent.company_id == context.company_id,
                AttendanceEvent.attachment_file_id == file_id,
            )
        )
        if scoped_members is not None:
            query = query.where(AttendanceRecord.membership_id.in_(scoped_members))
        if await referenced_for_members(query):
            return True
    if Permission.TASKS_VIEW.value in permissions:
        task_ids = (
            select(TaskComment.task_id)
            .where(
                TaskComment.company_id == context.company_id,
                TaskComment.attachment_file_id == file_id,
            )
            .union(
                select(WorkTask.id).where(
                    WorkTask.company_id == context.company_id,
                    WorkTask.completion_attachment_file_id == file_id,
                )
            )
        )
        # A task receipt/comment is visible to every member who can see the
        # task, including its creator (owner/manager), not only assignees.
        # Previously the query only selected TaskAssignee rows, so an owner
        # who created a task could see the receipt link but received 403 when
        # opening it.
        query = select(WorkTask.id).where(
            WorkTask.company_id == context.company_id,
            WorkTask.id.in_(task_ids),
            or_(
                WorkTask.created_by_membership_id == member_id,
                WorkTask.id.in_(
                    select(TaskAssignee.task_id).where(
                        TaskAssignee.company_id == context.company_id,
                        TaskAssignee.membership_id == member_id,
                    )
                ),
            ),
        )
        if scoped_members is not None:
            query = query.where(
                or_(
                    WorkTask.created_by_membership_id.in_(scoped_members),
                    WorkTask.id.in_(
                        select(TaskAssignee.task_id).where(
                            TaskAssignee.company_id == context.company_id,
                            TaskAssignee.membership_id.in_(scoped_members),
                        )
                    ),
                )
            )
        if await referenced_for_members(query):
            return True
    return False


@router.post("", response_model=FileResponse, status_code=201)
async def upload_file(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    upload: Annotated[UploadFile, File()],
) -> FileResponse:
    _user, company, membership = auth_session
    subscription = await active_subscription(session, company.id)
    if subscription is None:
        raise ProblemError(
            status=403,
            code="subscription_inactive",
            title="Subscription inactive",
            detail="File uploads require an active subscription.",
        )
    content_type = upload.content_type or "application/octet-stream"
    filename = (upload.filename or "upload").replace("\r", "").replace("\n", "")[:255]
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension in VIDEO_EXTENSIONS:
        raise ProblemError(
            status=415,
            code="video_upload_not_allowed",
            title="Video uploads are not allowed",
            detail="Attach an image, PDF, document, spreadsheet, or audio file instead of a video.",
        )
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ProblemError(
            status=415,
            code="file_type_not_allowed",
            title="File type not allowed",
            detail="Upload a supported image, PDF, text, Word, Excel, or audio file.",
        )
    content = await upload.read(MAX_FILE_BYTES + 1)
    if not content or len(content) > MAX_FILE_BYTES:
        raise ProblemError(
            status=413,
            code="file_size_invalid",
            title="File size invalid",
            detail="Files must be non-empty and no larger than 10 MB.",
        )
    storage_limit = (
        plan_limit(subscription[1], "storage_mb", subscription[0].limits_override)
        * 1024
        * 1024
    )
    used = int(
        await session.scalar(
            select(func.coalesce(func.sum(StoredFile.size_bytes), 0)).where(
                StoredFile.company_id == company.id
            )
        )
        or 0
    )
    if used + len(content) > storage_limit:
        raise ProblemError(
            status=403,
            code="subscription_storage_limit",
            title="Storage limit reached",
            detail="Delete files or upgrade the subscription before uploading.",
        )
    item = StoredFile(
        company_id=company.id,
        uploaded_by_membership_id=membership.id,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
        content=content,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return FileResponse(
        id=item.id,
        filename=item.original_filename,
        content_type=item.content_type,
        size_bytes=item.size_bytes,
        sha256=item.sha256,
    )


@router.get("/{file_id}")
async def download_file(
    file_id: UUID, auth_session: CurrentAuthSession, session: DatabaseSession
) -> Response:
    _user, company, membership = auth_session
    item = await session.scalar(
        select(StoredFile).where(StoredFile.company_id == company.id, StoredFile.id == file_id)
    )
    if item is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="file_not_found",
            title="File not found",
            detail="The file does not exist in this company.",
        )
    if item.uploaded_by_membership_id != membership.id and not await can_download_linked_file(
        session, auth_session, item.id
    ):
        raise ProblemError(
            status=403,
            code="file_access_denied",
            title="File access denied",
            detail="The file is not linked to a resource visible to this member.",
        )
    return Response(
        content=item.content,
        media_type=item.content_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{quote(item.original_filename, safe='')}"
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
