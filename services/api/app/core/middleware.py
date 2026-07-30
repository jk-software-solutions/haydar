from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.request_context import reset_request_id, set_request_id


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        candidate = request.headers.get("X-Request-ID")
        try:
            request_id = str(UUID(candidate)) if candidate else str(uuid4())
        except ValueError:
            request_id = str(uuid4())

        token = set_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            reset_request_id(token)
