from fastapi import APIRouter

from app.api.v1.access import router as access_router
from app.api.v1.attendance import permissions_router, presence_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.branches import branches_router, departments_router
from app.api.v1.devices import router as devices_router
from app.api.v1.files import router as files_router
from app.api.v1.geofence_exits import router as geofence_exits_router
from app.api.v1.groups import router as groups_router
from app.api.v1.health import router as health_router
from app.api.v1.invitations import activation_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.organization import companies_router, employees_router
from app.api.v1.platform_admin import router as platform_router
from app.api.v1.reports import router as reports_router
from app.api.v1.shifts import router as shifts_router
from app.api.v1.workforce import (
    documents_router,
    leave_router,
    notifications_router,
    tasks_router,
)

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(
    activation_router,
    prefix="/auth/invitations",
    tags=["auth"],
)
api_router.include_router(invitations_router, prefix="/invitations", tags=["invitations"])
api_router.include_router(access_router, prefix="/members", tags=["member-access"])
api_router.include_router(devices_router, prefix="/devices", tags=["devices"])
api_router.include_router(branches_router, prefix="/branches", tags=["branches"])
api_router.include_router(departments_router, prefix="/departments", tags=["departments"])
api_router.include_router(groups_router, prefix="/groups", tags=["groups"])
api_router.include_router(shifts_router, prefix="/shifts", tags=["shifts"])
api_router.include_router(attendance_router, prefix="/attendance", tags=["attendance"])
api_router.include_router(
    geofence_exits_router, prefix="/geofence-exit-events", tags=["geofence-exits"]
)
api_router.include_router(permissions_router, prefix="/permission-requests", tags=["permissions"])
api_router.include_router(presence_router, prefix="/presence-requests", tags=["presence"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(leave_router, prefix="/leave", tags=["leave"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(billing_router, prefix="/billing", tags=["billing"])
api_router.include_router(platform_router, prefix="/platform", tags=["platform"])
api_router.include_router(files_router, prefix="/files", tags=["files"])
api_router.include_router(companies_router, prefix="/companies", tags=["companies"])
api_router.include_router(employees_router, prefix="/employees", tags=["employees"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
