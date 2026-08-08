from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemError
from app.models.identity import (
    Company,
    CompanyMembership,
    MembershipRole,
    RolePermission,
    User,
)


class RoleCode(StrEnum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    SUPERVISOR = "SUPERVISOR"
    HR_OFFICER = "HR_OFFICER"
    EMPLOYEE = "EMPLOYEE"


class Permission(StrEnum):
    MEMBERS_VIEW = "members:view"
    MEMBERS_CREATE = "members:create"
    MEMBERS_MANAGE = "members:manage"
    SETTINGS_MANAGE = "settings:manage"
    DEVICES_VIEW = "devices:view"
    DEVICES_MANAGE = "devices:manage"
    BRANCHES_VIEW = "branches:view"
    BRANCHES_MANAGE = "branches:manage"
    DEPARTMENTS_VIEW = "departments:view"
    DEPARTMENTS_MANAGE = "departments:manage"
    ASSIGNMENTS_VIEW = "assignments:view"
    ASSIGNMENTS_MANAGE = "assignments:manage"
    SHIFTS_VIEW = "shifts:view"
    SHIFTS_MANAGE = "shifts:manage"
    ATTENDANCE_VIEW = "attendance:view"
    ATTENDANCE_MANAGE = "attendance:manage"
    PERMISSIONS_VIEW = "permissions:view"
    PERMISSIONS_MANAGE = "permissions:manage"
    PRESENCE_MANAGE = "presence:manage"
    TASKS_VIEW = "tasks:view"
    TASKS_MANAGE = "tasks:manage"
    LEAVE_VIEW = "leave:view"
    LEAVE_MANAGE = "leave:manage"
    DOCUMENTS_VIEW = "documents:view"
    DOCUMENTS_MANAGE = "documents:manage"
    REPORTS_VIEW = "reports:view"
    REPORTS_EXPORT = "reports:export"
    SUBSCRIPTION_VIEW = "subscription:view"
    SUBSCRIPTION_MANAGE = "subscription:manage"


@dataclass(frozen=True, slots=True)
class TenantContext:
    company_id: UUID
    user: User
    company: Company
    membership: CompanyMembership


def tenant_context(
    auth_session: tuple[User, Company, CompanyMembership],
) -> TenantContext:
    user, company, membership = auth_session
    return TenantContext(
        company_id=company.id,
        user=user,
        company=company,
        membership=membership,
    )


async def require_permission(
    session: AsyncSession,
    context: TenantContext,
    permission: Permission,
) -> None:
    granted = await session.scalar(
        select(RolePermission.permission_code)
        .join(
            MembershipRole,
            MembershipRole.role_code == RolePermission.role_code,
        )
        .where(
            MembershipRole.company_id == context.company_id,
            MembershipRole.membership_id == context.membership.id,
            RolePermission.permission_code == permission.value,
        )
        .limit(1)
    )
    if granted is None:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail=f"The current role cannot perform {permission.value}.",
        )
