from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from fastapi import status

from app.core.errors import ProblemError
from app.models.identity import Company, CompanyMembership, User


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


ROLE_PERMISSIONS: dict[RoleCode, frozenset[Permission]] = {
    RoleCode.OWNER: frozenset(Permission),
    RoleCode.MANAGER: frozenset(
        {Permission.MEMBERS_VIEW, Permission.MEMBERS_CREATE, Permission.MEMBERS_MANAGE}
    ),
    RoleCode.HR_OFFICER: frozenset(
        {Permission.MEMBERS_VIEW, Permission.MEMBERS_CREATE, Permission.MEMBERS_MANAGE}
    ),
    RoleCode.SUPERVISOR: frozenset({Permission.MEMBERS_VIEW}),
    RoleCode.EMPLOYEE: frozenset(),
}


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


def require_permission(context: TenantContext, permission: Permission) -> None:
    try:
        role = RoleCode(context.membership.role_code)
    except ValueError as exc:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The membership role is not recognized.",
        ) from exc
    if permission not in ROLE_PERMISSIONS[role]:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail=f"The current role cannot perform {permission.value}.",
        )
