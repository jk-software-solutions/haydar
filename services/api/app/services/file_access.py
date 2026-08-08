from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import TenantContext
from app.core.errors import ProblemError
from app.models.files import StoredFile


async def require_owned_attachment(
    session: AsyncSession,
    context: TenantContext,
    file_id: UUID | None,
) -> StoredFile | None:
    if file_id is None:
        return None
    item = await session.scalar(
        select(StoredFile).where(
            StoredFile.company_id == context.company_id,
            StoredFile.id == file_id,
            StoredFile.uploaded_by_membership_id == context.membership.id,
        )
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="attachment_not_found",
            title="Attachment not found",
            detail="Use a file uploaded by the current member in this company.",
        )
    return item
