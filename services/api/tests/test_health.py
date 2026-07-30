import httpx

from app.db.session import check_database
from app.main import app


async def database_is_ready() -> bool:
    return True


async def database_is_unavailable() -> bool:
    return False


async def test_liveness_returns_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "haydar-api"}
    assert response.headers["X-Request-ID"]


async def test_readiness_succeeds_when_database_is_ready(client: httpx.AsyncClient) -> None:
    app.dependency_overrides[check_database] = database_is_ready
    try:
        response = await client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


async def test_readiness_uses_problem_details(client: httpx.AsyncClient) -> None:
    app.dependency_overrides[check_database] = database_is_unavailable
    try:
        response = await client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "database_unavailable"
