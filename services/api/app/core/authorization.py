from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProblemError
from app.models.identity import (
    Company,
    CompanyMembership,
    MembershipBranchScope,
    MembershipDepartmentScope,
    MembershipGroupScope,
    MembershipPermissionOverride,
    MembershipRole,
    RolePermission,
    User,
)
from app.models.organization import (
    EmployeeBranchAssignment,
    EmployeeGroupMembership,
    EmployeeProfile,
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
    GEOFENCE_EXITS_VIEW = "geofence_exits:view"
    GEOFENCE_EXITS_MANAGE = "geofence_exits:manage"
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
    override = await session.scalar(
        select(MembershipPermissionOverride.allowed).where(
            MembershipPermissionOverride.company_id == context.company_id,
            MembershipPermissionOverride.membership_id == context.membership.id,
            MembershipPermissionOverride.permission_code == permission.value,
        )
    )
    if override is not None:
        if override:
            return
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail=f"The current membership is denied {permission.value}.",
        )
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


async def membership_roles(
    session: AsyncSession, company_id: UUID, membership_id: UUID
) -> list[str]:
    values = await session.scalars(
        select(MembershipRole.role_code)
        .where(
            MembershipRole.company_id == company_id,
            MembershipRole.membership_id == membership_id,
        )
        .order_by(MembershipRole.role_code)
    )
    return list(values)


async def effective_permission_codes(
    session: AsyncSession, company_id: UUID, membership_id: UUID
) -> list[str]:
    role_permissions = set(
        await session.scalars(
            select(RolePermission.permission_code)
            .join(MembershipRole, MembershipRole.role_code == RolePermission.role_code)
            .where(
                MembershipRole.company_id == company_id,
                MembershipRole.membership_id == membership_id,
            )
        )
    )
    overrides = await session.execute(
        select(
            MembershipPermissionOverride.permission_code,
            MembershipPermissionOverride.allowed,
        ).where(
            MembershipPermissionOverride.company_id == company_id,
            MembershipPermissionOverride.membership_id == membership_id,
        )
    )
    for code, allowed in overrides:
        if allowed:
            role_permissions.add(code)
        else:
            role_permissions.discard(code)
    return sorted(role_permissions)


@dataclass(frozen=True, slots=True)
class MembershipScopes:
    unrestricted: bool
    branch_ids: frozenset[UUID]
    department_ids: frozenset[UUID]
    group_ids: frozenset[UUID]


async def membership_scopes(session: AsyncSession, context: TenantContext) -> MembershipScopes:
    roles = set(await membership_roles(session, context.company_id, context.membership.id))
    if roles.intersection({RoleCode.OWNER.value, RoleCode.HR_OFFICER.value}):
        return MembershipScopes(True, frozenset(), frozenset(), frozenset())
    branch_ids = frozenset(
        await session.scalars(
            select(MembershipBranchScope.branch_id).where(
                MembershipBranchScope.company_id == context.company_id,
                MembershipBranchScope.membership_id == context.membership.id,
            )
        )
    )
    department_ids = frozenset(
        await session.scalars(
            select(MembershipDepartmentScope.department_id).where(
                MembershipDepartmentScope.company_id == context.company_id,
                MembershipDepartmentScope.membership_id == context.membership.id,
            )
        )
    )
    group_ids = frozenset(
        await session.scalars(
            select(MembershipGroupScope.group_id).where(
                MembershipGroupScope.company_id == context.company_id,
                MembershipGroupScope.membership_id == context.membership.id,
            )
        )
    )
    return MembershipScopes(False, branch_ids, department_ids, group_ids)


async def visible_membership_ids(
    session: AsyncSession, context: TenantContext
) -> frozenset[UUID] | None:
    """Return ``None`` for unrestricted access or the exact visible member IDs."""

    scopes = await membership_scopes(session, context)
    if scopes.unrestricted:
        return None
    visible: set[UUID] = {context.membership.id}
    today = datetime.now(UTC).date()
    if scopes.branch_ids:
        visible.update(
            await session.scalars(
                select(EmployeeBranchAssignment.membership_id).where(
                    EmployeeBranchAssignment.company_id == context.company_id,
                    EmployeeBranchAssignment.branch_id.in_(scopes.branch_ids),
                    EmployeeBranchAssignment.effective_from <= today,
                    (
                        EmployeeBranchAssignment.effective_to.is_(None)
                        | (EmployeeBranchAssignment.effective_to >= today)
                    ),
                )
            )
        )
    if scopes.department_ids:
        visible.update(
            await session.scalars(
                select(EmployeeProfile.membership_id).where(
                    EmployeeProfile.company_id == context.company_id,
                    EmployeeProfile.department_id.in_(scopes.department_ids),
                )
            )
        )
    if scopes.group_ids:
        visible.update(
            await session.scalars(
                select(EmployeeGroupMembership.membership_id).where(
                    EmployeeGroupMembership.company_id == context.company_id,
                    EmployeeGroupMembership.group_id.in_(scopes.group_ids),
                )
            )
        )
    return frozenset(visible)


async def require_membership_scope(
    session: AsyncSession, context: TenantContext, membership_id: UUID
) -> None:
    visible = await visible_membership_ids(session, context)
    if visible is not None and membership_id not in visible:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="resource_not_found",
            title="Resource not found",
            detail="The resource does not exist in the current access scope.",
        )


async def require_branch_scope(
    session: AsyncSession, context: TenantContext, branch_id: UUID
) -> None:
    scopes = await membership_scopes(session, context)
    if scopes.unrestricted or branch_id in scopes.branch_ids:
        return
    own_branch = await session.scalar(
        select(EmployeeBranchAssignment.branch_id).where(
            EmployeeBranchAssignment.company_id == context.company_id,
            EmployeeBranchAssignment.membership_id == context.membership.id,
            EmployeeBranchAssignment.branch_id == branch_id,
            EmployeeBranchAssignment.effective_to.is_(None),
        )
    )
    if own_branch is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="resource_not_found",
            title="Resource not found",
            detail="The resource does not exist in the current access scope.",
        )


async def require_department_scope(
    session: AsyncSession, context: TenantContext, department_id: UUID
) -> None:
    scopes = await membership_scopes(session, context)
    if scopes.unrestricted or department_id in scopes.department_ids:
        return
    own_department = await session.scalar(
        select(EmployeeProfile.department_id).where(
            EmployeeProfile.company_id == context.company_id,
            EmployeeProfile.membership_id == context.membership.id,
            EmployeeProfile.department_id == department_id,
        )
    )
    if own_department is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="resource_not_found",
            title="Resource not found",
            detail="The resource does not exist in the current access scope.",
        )


async def require_group_scope(
    session: AsyncSession, context: TenantContext, group_id: UUID
) -> None:
    scopes = await membership_scopes(session, context)
    if scopes.unrestricted or group_id in scopes.group_ids:
        return
    own_group = await session.scalar(
        select(EmployeeGroupMembership.group_id).where(
            EmployeeGroupMembership.company_id == context.company_id,
            EmployeeGroupMembership.membership_id == context.membership.id,
            EmployeeGroupMembership.group_id == group_id,
        )
    )
    if own_group is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="resource_not_found",
            title="Resource not found",
            detail="The resource does not exist in the current access scope.",
        )


async def require_unrestricted_scope(session: AsyncSession, context: TenantContext) -> None:
    if not (await membership_scopes(session, context)).unrestricted:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="unrestricted_scope_required",
            title="Unrestricted scope required",
            detail="This operation affects the full company and requires unrestricted access.",
        )
