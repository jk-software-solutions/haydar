from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.errors import ProblemError
from app.db.session import check_database

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["haydar-api"] = "haydar-api"


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def ready(database_ok: Annotated[bool, Depends(check_database)]) -> HealthResponse:
    if not database_ok:
        raise ProblemError(
            status=503,
            code="database_unavailable",
            title="Service is not ready",
            detail="The database is not configured or did not pass its readiness check.",
        )
    return HealthResponse(status="ok")
