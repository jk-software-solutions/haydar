from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import PermissionDefinition, Role, RolePermission

BUILTIN_ROLES: dict[str, str] = {
    "OWNER": "Company owner",
    "MANAGER": "Company manager",
    "SUPERVISOR": "Supervisor",
    "HR_OFFICER": "HR officer",
    "EMPLOYEE": "Employee",
}

BUILTIN_PERMISSIONS: dict[str, str] = {
    "members:view": "View company memberships and invitations",
    "members:create": "Invite new company members",
    "members:manage": "Update company memberships and roles",
    "settings:manage": "Manage company settings",
    "devices:view": "View company device registrations and change requests",
    "devices:manage": "Approve or reject employee device changes",
}

ROLE_PERMISSION_CODES: dict[str, frozenset[str]] = {
    "OWNER": frozenset(BUILTIN_PERMISSIONS),
    "MANAGER": frozenset(
        {"members:view", "members:create", "members:manage", "devices:view", "devices:manage"}
    ),
    "HR_OFFICER": frozenset(
        {"members:view", "members:create", "members:manage", "devices:view", "devices:manage"}
    ),
    "SUPERVISOR": frozenset({"members:view", "devices:view"}),
    "EMPLOYEE": frozenset(),
}


async def seed_builtin_rbac(session: AsyncSession) -> None:
    session.add_all([Role(code=code, display_name=name) for code, name in BUILTIN_ROLES.items()])
    session.add_all(
        [
            PermissionDefinition(code=code, description=description)
            for code, description in BUILTIN_PERMISSIONS.items()
        ]
    )
    session.add_all(
        [
            RolePermission(role_code=role_code, permission_code=permission_code)
            for role_code, permissions in ROLE_PERMISSION_CODES.items()
            for permission_code in permissions
        ]
    )
    await session.flush()
