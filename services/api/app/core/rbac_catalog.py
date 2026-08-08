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
    "branches:view": "View company branches",
    "branches:manage": "Create and update company branches",
    "departments:view": "View company departments",
    "departments:manage": "Create and update company departments",
    "assignments:view": "View employee branch assignment history",
    "assignments:manage": "Assign and transfer employees between branches",
    "shifts:view": "View company shifts and assignments",
    "shifts:manage": "Create and assign company shifts",
    "attendance:view": "View tenant attendance records",
    "attendance:manage": "Create and correct attendance records",
    "permissions:view": "View employee permission requests",
    "permissions:manage": "Review employee permission requests",
    "presence:manage": "Create and review presence requests",
    "geofence_exits:view": "View unauthorized geofence exit events",
    "geofence_exits:manage": "Review unauthorized geofence exit events",
    "tasks:view": "View assigned tenant tasks",
    "tasks:manage": "Create and manage tenant tasks",
    "leave:view": "View tenant leave requests and balances",
    "leave:manage": "Manage leave types, balances, and approvals",
    "documents:view": "View tenant employee documents",
    "documents:manage": "Manage and review employee documents",
    "reports:view": "View tenant workforce reports",
    "reports:export": "Export tenant reports",
    "subscription:view": "View the company subscription",
    "subscription:manage": "Manage company subscription requests",
}

ROLE_PERMISSION_CODES: dict[str, frozenset[str]] = {
    "OWNER": frozenset(BUILTIN_PERMISSIONS),
    "MANAGER": frozenset(
        {
            "members:view",
            "members:create",
            "members:manage",
            "devices:view",
            "devices:manage",
            "branches:view",
            "branches:manage",
            "departments:view",
            "departments:manage",
            "assignments:view",
            "assignments:manage",
            "shifts:view",
            "shifts:manage",
            "attendance:view",
            "attendance:manage",
            "permissions:view",
            "permissions:manage",
            "presence:manage",
            "geofence_exits:view",
            "geofence_exits:manage",
            "tasks:view",
            "tasks:manage",
            "leave:view",
            "leave:manage",
            "documents:view",
            "documents:manage",
            "reports:view",
            "reports:export",
            "subscription:view",
            "subscription:manage",
        }
    ),
    "HR_OFFICER": frozenset(
        {
            "members:view",
            "members:create",
            "members:manage",
            "devices:view",
            "devices:manage",
            "branches:view",
            "branches:manage",
            "departments:view",
            "departments:manage",
            "assignments:view",
            "assignments:manage",
            "shifts:view",
            "shifts:manage",
            "attendance:view",
            "attendance:manage",
            "permissions:view",
            "permissions:manage",
            "presence:manage",
            "geofence_exits:view",
            "geofence_exits:manage",
            "tasks:view",
            "tasks:manage",
            "leave:view",
            "leave:manage",
            "documents:view",
            "documents:manage",
            "reports:view",
            "reports:export",
            "subscription:view",
            "subscription:manage",
        }
    ),
    "SUPERVISOR": frozenset(
        {
            "members:view",
            "devices:view",
            "branches:view",
            "departments:view",
            "assignments:view",
            "shifts:view",
            "attendance:view",
            "permissions:view",
            "permissions:manage",
            "presence:manage",
            "geofence_exits:view",
            "geofence_exits:manage",
            "tasks:view",
            "tasks:manage",
            "leave:view",
            "documents:view",
            "reports:view",
            "reports:export",
            "subscription:view",
        }
    ),
    "EMPLOYEE": frozenset(
        {
            "branches:view",
            "departments:view",
            "shifts:view",
            "attendance:view",
            "permissions:view",
            "tasks:view",
            "leave:view",
            "documents:view",
            "subscription:view",
        }
    ),
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
