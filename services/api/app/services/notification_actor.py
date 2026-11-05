from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import CompanyMembership, User
from app.models.organization import EmployeeProfile


async def membership_actor_name(
    session: AsyncSession, company_id: UUID, membership_id: UUID
) -> str | None:
    """Return the human name that should accompany an activity notification."""
    profile_name = await session.scalar(
        select(EmployeeProfile.display_name).where(
            EmployeeProfile.company_id == company_id,
            EmployeeProfile.membership_id == membership_id,
        )
    )
    if profile_name:
        return profile_name
    return await session.scalar(
        select(User.full_name)
        .join(CompanyMembership, CompanyMembership.user_id == User.id)
        .where(
            CompanyMembership.company_id == company_id,
            CompanyMembership.id == membership_id,
        )
    )
