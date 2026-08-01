from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.branches import branches_router, departments_router
from app.api.v1.devices import router as devices_router
from app.api.v1.health import router as health_router
from app.api.v1.invitations import activation_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.organization import companies_router, employees_router
from app.api.v1.shifts import router as shifts_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(
    activation_router,
    prefix="/auth/invitations",
    tags=["auth"],
)
api_router.include_router(invitations_router, prefix="/invitations", tags=["invitations"])
api_router.include_router(devices_router, prefix="/devices", tags=["devices"])
api_router.include_router(branches_router, prefix="/branches", tags=["branches"])
api_router.include_router(departments_router, prefix="/departments", tags=["departments"])
api_router.include_router(shifts_router, prefix="/shifts", tags=["shifts"])
api_router.include_router(companies_router, prefix="/companies", tags=["companies"])
api_router.include_router(employees_router, prefix="/employees", tags=["employees"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
