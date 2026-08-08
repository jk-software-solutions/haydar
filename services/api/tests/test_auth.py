import httpx
import pytest

from app.services import email_delivery


async def register_owner(client: httpx.AsyncClient) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register-company",
        json={
            "company_name": "Jawad Sites",
            "owner_full_name": "Jawad Owner",
            "owner_email": "owner@example.com",
            "password": "ChangeMe123!",
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_register_company_returns_owner_session(db_client: httpx.AsyncClient) -> None:
    payload = await register_owner(db_client)

    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["session"]["user"]["email"] == "owner@example.com"
    assert payload["session"]["company"]["display_name"] == "Jawad Sites"
    assert payload["session"]["roles"] == ["OWNER"]


async def test_login_and_session_use_real_tokens(db_client: httpx.AsyncClient) -> None:
    await register_owner(db_client)

    login_response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "OWNER@example.com", "password": "ChangeMe123!"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()

    session_response = await db_client.get(
        "/api/v1/auth/session",
        headers={"Authorization": f"Bearer {login_payload['access_token']}"},
    )
    assert session_response.status_code == 200
    assert session_response.json()["roles"] == ["OWNER"]


async def test_login_rejects_invalid_password(db_client: httpx.AsyncClient) -> None:
    await register_owner(db_client)

    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "WrongPass123!"},
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_credentials"


async def test_refresh_rotates_refresh_session(db_client: httpx.AsyncClient) -> None:
    payload = await register_owner(db_client)

    refresh_response = await db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": payload["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["refresh_token"] != payload["refresh_token"]

    reused_response = await db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": payload["refresh_token"]},
    )
    assert reused_response.status_code == 401


async def test_password_reset_is_single_use_and_revokes_sessions(
    db_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_session = await register_owner(db_client)
    delivered: list[tuple[str, str]] = []

    async def capture_reset(*, recipient: str, token: str) -> bool:
        delivered.append((recipient, token))
        return True

    monkeypatch.setattr(email_delivery, "send_password_reset_email", capture_reset)
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "smtp_from_email", "security@example.com")

    request_response = await db_client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "OWNER@example.com"},
    )
    unknown_response = await db_client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "missing@example.com"},
    )
    assert request_response.status_code == 202
    assert unknown_response.status_code == 202
    assert request_response.json() == unknown_response.json()
    assert delivered[0][0] == "owner@example.com"

    reset_token = delivered[0][1]
    reset_response = await db_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "NewSecure456!"},
    )
    assert reset_response.status_code == 204

    old_refresh = await db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_session["refresh_token"]},
    )
    assert old_refresh.status_code == 401
    reused = await db_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "AnotherSecure789!"},
    )
    assert reused.status_code == 400
    assert reused.json()["code"] == "password_reset_invalid"

    old_login = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "ChangeMe123!"},
    )
    new_login = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "NewSecure456!"},
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200
