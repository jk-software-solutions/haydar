import httpx


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
