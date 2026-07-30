from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_context import get_request_id


class ProblemError(Exception):
    def __init__(self, *, status: int, code: str, title: str, detail: str) -> None:
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail


def problem_payload(
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    field_errors: Sequence[Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": f"https://api.haydar/errors/{code}",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        "request_id": get_request_id(),
    }
    if field_errors is not None:
        payload["field_errors"] = list(field_errors)
    return payload


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def handle_problem(_request: Request, exc: ProblemError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            media_type="application/problem+json",
            content=problem_payload(
                status=exc.status,
                code=exc.code,
                title=exc.title,
                detail=exc.detail,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            media_type="application/problem+json",
            content=problem_payload(
                status=422,
                code="validation_error",
                title="Request validation failed",
                detail="One or more fields are invalid.",
                field_errors=exc.errors(),
            ),
        )
