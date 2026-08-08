from typing import Any
from uuid import uuid4

import httpx


def auth_headers(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def register_company(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register-company",
        json={
            "company_name": "Phone Login Company",
            "owner_full_name": "Phone Login Owner",
            "owner_email": "phone-owner@example.com",
            "password": "ChangeMe123!",
        },
    )
    assert response.status_code == 201
    return response.json()


async def invite_employee(
    client: httpx.AsyncClient, owner: dict[str, Any], email: str
) -> dict[str, Any]:
    invitation = await client.post(
        "/api/v1/invitations",
        headers=auth_headers(owner),
        json={"email": email, "full_name": "Phone Employee", "role_code": "EMPLOYEE"},
    )
    assert invitation.status_code == 201
    activation = await client.post(
        "/api/v1/auth/invitations/activate",
        json={
            "activation_token": invitation.json()["activation_token"],
            "password": "EmployeePass123!",
        },
    )
    assert activation.status_code == 200
    return activation.json()


async def profile_for(
    client: httpx.AsyncClient, owner: dict[str, Any], membership_id: str
) -> dict[str, Any]:
    response = await client.get(f"/api/v1/employees/{membership_id}", headers=auth_headers(owner))
    assert response.status_code == 200
    return response.json()


async def test_phone_login_requires_unique_administrator_verified_e164_identity(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(db_client)
    employee = await invite_employee(db_client, owner, "phone-worker@example.com")
    second = await invite_employee(db_client, owner, "phone-worker-2@example.com")
    employee_id = employee["session"]["membership_id"]
    second_id = second["session"]["membership_id"]

    unavailable = await db_client.post(
        "/api/v1/auth/login",
        json={"identifier": "+966500000111", "password": "EmployeePass123!"},
    )
    assert unavailable.status_code == 401

    profile = await profile_for(db_client, owner, employee_id)
    invalid = await db_client.patch(
        f"/api/v1/employees/{employee_id}",
        headers=auth_headers(owner),
        json={"version": profile["version"], "phone": "0500000111"},
    )
    assert invalid.status_code == 422

    updated = await db_client.patch(
        f"/api/v1/employees/{employee_id}",
        headers=auth_headers(owner),
        json={"version": profile["version"], "phone": "+966 50 000 0111"},
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+966500000111"
    assert updated.json()["phone_login_enabled"] is True

    phone_login = await db_client.post(
        "/api/v1/auth/login",
        json={"identifier": "+966-50-000-0111", "password": "EmployeePass123!"},
    )
    assert phone_login.status_code == 200
    assert phone_login.json()["session"]["user"]["email"] == "phone-worker@example.com"

    second_profile = await profile_for(db_client, owner, second_id)
    duplicate = await db_client.patch(
        f"/api/v1/employees/{second_id}",
        headers=auth_headers(owner),
        json={"version": second_profile["version"], "phone": "+966500000111"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "phone_already_registered"

    installation_id = str(uuid4())
    device = await db_client.post(
        "/api/v1/devices/register",
        headers={**auth_headers(second), "X-Installation-ID": installation_id},
        json={
            "installation_id": installation_id,
            "platform": "android",
            "device_name": "Employee phone",
        },
    )
    assert device.status_code == 201
    deactivated = await db_client.post(
        f"/api/v1/employees/{second_id}/status",
        headers=auth_headers(owner),
        json={
            "version": second_profile["membership_version"],
            "status": "inactive",
            "reason": "Employee offboarding completed",
        },
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["membership_status"] == "inactive"
    rejected_session = await db_client.get("/api/v1/auth/session", headers=auth_headers(second))
    assert rejected_session.status_code == 401
    rejected_refresh = await db_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}
    )
    assert rejected_refresh.status_code == 401
    reactivated = await db_client.post(
        f"/api/v1/employees/{second_id}/status",
        headers=auth_headers(owner),
        json={
            "version": deactivated.json()["membership_version"],
            "status": "active",
            "reason": "Employee returned to active service",
        },
    )
    assert reactivated.status_code == 200
    relogin = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "phone-worker-2@example.com", "password": "EmployeePass123!"},
    )
    assert relogin.status_code == 200

    cleared = await db_client.patch(
        f"/api/v1/employees/{employee_id}",
        headers=auth_headers(owner),
        json={"version": updated.json()["version"], "phone": None},
    )
    assert cleared.status_code == 200
    disabled = await db_client.post(
        "/api/v1/auth/login",
        json={"identifier": "+966500000111", "password": "EmployeePass123!"},
    )
    assert disabled.status_code == 401
