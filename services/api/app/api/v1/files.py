from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.errors import ProblemError
from app.core.subscription_catalog import active_subscription, plan_limit
from app.db.session import get_session
from app.models.files import StoredFile

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
}
MAX_FILE_BYTES = 10 * 1024 * 1024


class FileResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


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
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ProblemError(
            status=415,
            code="file_type_not_allowed",
            title="File type not allowed",
            detail="Upload a supported image, PDF, text, Word, or Excel file.",
        )
    content = await upload.read(MAX_FILE_BYTES + 1)
    if not content or len(content) > MAX_FILE_BYTES:
        raise ProblemError(
            status=413,
            code="file_size_invalid",
            title="File size invalid",
            detail="Files must be non-empty and no larger than 10 MB.",
        )
    storage_limit = plan_limit(subscription[1], "storage_mb") * 1024 * 1024
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
    filename = (upload.filename or "upload").replace("\r", "").replace("\n", "")[:255]
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
    if membership.role_code == "EMPLOYEE" and item.uploaded_by_membership_id != membership.id:
        raise ProblemError(
            status=403,
            code="file_access_denied",
            title="File access denied",
            detail="Employees can only download files they uploaded.",
        )
    return Response(
        content=item.content,
        media_type=item.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{item.original_filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
