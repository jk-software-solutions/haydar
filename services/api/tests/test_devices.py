from uuid import uuid4

import httpx


async def register_company(
    client: httpx.AsyncClient, company_name: str, email: str
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register-company",
        json={
            "company_name": company_name,
            "owner_full_name": f"Owner {company_name}",
            "owner_email": email,
            "password": "ChangeMe123!",
        },
    )
    assert response.status_code == 201
    return response.json()


def headers(session: dict[str, object]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def invite_employee(
    client: httpx.AsyncClient,
    owner: dict[str, object],
) -> dict[str, object]:
    invitation = await client.post(
        "/api/v1/invitations",
        headers=headers(owner),
        json={
            "email": "device-employee@example.com",
            "full_name": "Device Employee",
            "role_code": "EMPLOYEE",
        },
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


async def test_first_device_and_tenant_scoped_change_approval(
    db_client: httpx.AsyncClient,
) -> None:
    owner_a = await register_company(db_client, "Device Company A", "device-a@example.com")
    owner_b = await register_company(db_client, "Device Company B", "device-b@example.com")
    employee = await invite_employee(db_client, owner_a)

    first_installation = str(uuid4())
    first = await db_client.post(
        "/api/v1/devices/register",
        headers=headers(employee),
        json={
            "installation_id": first_installation,
            "platform": "android",
            "device_name": "Employee Android",
            "public_key": "placeholder-device-public-key-value",
        },
    )
    assert first.status_code == 201
    assert first.json()["device"]["status"] == "approved"
    assert first.json()["requires_approval"] is False

    missing_reason = await db_client.post(
        "/api/v1/devices/register",
        headers=headers(employee),
        json={
            "installation_id": str(uuid4()),
            "platform": "android",
            "device_name": "Replacement Android",
        },
    )
    assert missing_reason.status_code == 422
    assert missing_reason.json()["code"] == "device_change_reason_required"

    replacement = await db_client.post(
        "/api/v1/devices/register",
        headers=headers(employee),
        json={
            "installation_id": str(uuid4()),
            "platform": "android",
            "device_name": "Replacement Android",
            "reason": "My previous phone is no longer available.",
        },
    )
    assert replacement.status_code == 201
    assert replacement.json()["device"]["status"] == "pending"
    request_id = replacement.json()["change_request_id"]

    own_changes = await db_client.get("/api/v1/devices/change-requests", headers=headers(owner_a))
    other_changes = await db_client.get("/api/v1/devices/change-requests", headers=headers(owner_b))
    assert own_changes.status_code == 200
    assert own_changes.json()["total"] == 1
    assert own_changes.json()["items"][0]["id"] == request_id
    assert other_changes.status_code == 200
    assert other_changes.json()["items"] == []

    employee_approval = await db_client.post(
        f"/api/v1/devices/change-requests/{request_id}/approve",
        headers=headers(employee),
        json={},
    )
    assert employee_approval.status_code == 403

    cross_tenant_approval = await db_client.post(
        f"/api/v1/devices/change-requests/{request_id}/approve",
        headers=headers(owner_b),
        json={},
    )
    assert cross_tenant_approval.status_code == 404
    assert cross_tenant_approval.json()["code"] == "device_change_not_found"

    approval = await db_client.post(
        f"/api/v1/devices/change-requests/{request_id}/approve",
        headers=headers(owner_a),
        json={"comment": "Identity confirmed with the employee."},
    )
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"

    devices = await db_client.get("/api/v1/devices/me", headers=headers(employee))
    assert devices.status_code == 200
    assert {device["status"] for device in devices.json()} == {"approved", "revoked"}
    assert sum(device["status"] == "approved" for device in devices.json()) == 1
