from asyncio import Lock
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from time import monotonic
from uuid import UUID, uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
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


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, *, general_limit: int, auth_limit: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.general_limit = general_limit
        self.auth_limit = auth_limit
        self.hits: defaultdict[str, deque[float]] = defaultdict(deque)
        self.lock = Lock()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method == "OPTIONS" or not request.url.path.startswith("/api/"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        is_auth = "/auth/" in request.url.path
        bucket = f"{client}:{'auth' if is_auth else 'api'}"
        limit = self.auth_limit if is_auth else self.general_limit
        now = monotonic()
        async with self.lock:
            entries = self.hits[bucket]
            while entries and entries[0] <= now - 60:
                entries.popleft()
            if len(entries) >= limit:
                retry_after = max(1, round(60 - (now - entries[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "type": "https://api.haydar/errors/rate_limit_exceeded",
                        "title": "Rate limit exceeded",
                        "status": 429,
                        "code": "rate_limit_exceeded",
                        "detail": "Too many requests. Retry after the indicated delay.",
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            entries.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        return response
