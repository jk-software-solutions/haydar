from datetime import date

import httpx


async def register_company(
    client: httpx.AsyncClient,
    company_name: str,
    email: str,
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
            "email": "branch-employee@example.com",
            "full_name": "Branch Employee",
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


def branch_payload(code: str, name: str, *, latitude: str = "24.713600") -> dict[str, object]:
    return {
        "code": code,
        "name": name,
        "saudi_short_address": "RRRD2929",
        "full_address": "King Fahd Road, Riyadh",
        "latitude": latitude,
        "longitude": "46.675300",
        "geofence_radius_m": 125,
        "timezone": "Asia/Riyadh",
        "working_hours": {"sun": ["08:00", "17:00"]},
    }


async def test_branch_department_crud_is_tenant_scoped(
    db_client: httpx.AsyncClient,
) -> None:
    owner_a = await register_company(db_client, "Branches A", "branches-a@example.com")
    owner_b = await register_company(db_client, "Branches B", "branches-b@example.com")
    employee = await invite_employee(db_client, owner_a)

    department = await db_client.post(
        "/api/v1/departments",
        headers=headers(owner_a),
        json={"code": "OPS", "name": "Operations"},
    )
    assert department.status_code == 201
    department_id = department.json()["id"]

    other_department = await db_client.get(
        f"/api/v1/departments/{department_id}",
        headers=headers(owner_b),
    )
    assert other_department.status_code == 404

    updated_department = await db_client.patch(
        f"/api/v1/departments/{department_id}",
        headers=headers(owner_a),
        json={"version": 1, "name": "Field Operations"},
    )
    assert updated_department.status_code == 200
    assert updated_department.json()["version"] == 2

    created = await db_client.post(
        "/api/v1/branches",
        headers=headers(owner_a),
        json=branch_payload("RUH-01", "Riyadh Main"),
    )
    assert created.status_code == 201
    branch = created.json()
    assert branch["code"] == "RUH-01"
    assert branch["geofence_radius_m"] == 125

    employee_list = await db_client.get("/api/v1/branches", headers=headers(employee))
    assert employee_list.status_code == 200
    assert employee_list.json()["total"] == 1

    forbidden_create = await db_client.post(
        "/api/v1/branches",
        headers=headers(employee),
        json=branch_payload("FORBIDDEN", "Forbidden"),
    )
    assert forbidden_create.status_code == 403

    other_list = await db_client.get("/api/v1/branches", headers=headers(owner_b))
    assert other_list.status_code == 200
    assert other_list.json()["items"] == []
    cross_tenant = await db_client.get(
        f"/api/v1/branches/{branch['id']}",
        headers=headers(owner_b),
    )
    assert cross_tenant.status_code == 404

    duplicate = await db_client.post(
        "/api/v1/branches",
        headers=headers(owner_a),
        json=branch_payload("RUH-01", "Duplicate"),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "branch_code_exists"

    rejected_company_id = await db_client.post(
        "/api/v1/branches",
        headers=headers(owner_a),
        json={
            **branch_payload("BAD-TENANT", "Bad Tenant"),
            "company_id": owner_b["session"]["company"]["id"],
        },
    )
    assert rejected_company_id.status_code == 422

    updated = await db_client.patch(
        f"/api/v1/branches/{branch['id']}",
        headers=headers(owner_a),
        json={"version": 1, "name": "Riyadh Headquarters", "geofence_radius_m": 150},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    stale = await db_client.patch(
        f"/api/v1/branches/{branch['id']}",
        headers=headers(owner_a),
        json={"version": 1, "name": "Stale"},
    )
    assert stale.status_code == 409


async def test_effective_branch_transfer_history_and_cross_tenant_rejection(
    db_client: httpx.AsyncClient,
) -> None:
    owner_a = await register_company(db_client, "Transfers A", "transfers-a@example.com")
    owner_b = await register_company(db_client, "Transfers B", "transfers-b@example.com")
    employee = await invite_employee(db_client, owner_a)
    membership_id = employee["session"]["membership_id"]

    first_branch_response = await db_client.post(
        "/api/v1/branches",
        headers=headers(owner_a),
        json=branch_payload("RUH", "Riyadh"),
    )
    second_branch_response = await db_client.post(
        "/api/v1/branches",
        headers=headers(owner_a),
        json=branch_payload("JED", "Jeddah", latitude="21.485800"),
    )
    other_branch_response = await db_client.post(
        "/api/v1/branches",
        headers=headers(owner_b),
        json=branch_payload("DMM", "Dammam", latitude="26.420700"),
    )
    assert first_branch_response.status_code == 201
    assert second_branch_response.status_code == 201
    assert other_branch_response.status_code == 201
    first_branch = first_branch_response.json()
    second_branch = second_branch_response.json()

    initial = await db_client.post(
        "/api/v1/branches/assignments",
        headers=headers(owner_a),
        json={
            "membership_id": membership_id,
            "branch_id": first_branch["id"],
            "effective_from": "2026-08-01",
            "reason": "Initial employee assignment",
        },
    )
    assert initial.status_code == 201

    duplicate = await db_client.post(
        "/api/v1/branches/assignments",
        headers=headers(owner_a),
        json={
            "membership_id": membership_id,
            "branch_id": first_branch["id"],
            "effective_from": "2026-08-02",
            "reason": "Duplicate current branch",
        },
    )
    assert duplicate.status_code == 409

    transfer = await db_client.post(
        "/api/v1/branches/assignments",
        headers=headers(owner_a),
        json={
            "membership_id": membership_id,
            "branch_id": second_branch["id"],
            "effective_from": "2026-08-10",
            "reason": "Operational transfer to Jeddah",
        },
    )
    assert transfer.status_code == 201
    assert transfer.json()["branch_code"] == "JED"

    history = await db_client.get(
        "/api/v1/branches/assignments/me",
        headers=headers(employee),
    )
    assert history.status_code == 200
    assert [item["branch_code"] for item in history.json()] == ["JED", "RUH"]
    assert history.json()[1]["effective_to"] == date(2026, 8, 9).isoformat()

    cross_tenant_history = await db_client.get(
        f"/api/v1/branches/assignments/{membership_id}",
        headers=headers(owner_b),
    )
    assert cross_tenant_history.status_code == 404
    assert cross_tenant_history.json()["code"] == "employee_not_found"

    cross_tenant_assignment = await db_client.post(
        "/api/v1/branches/assignments",
        headers=headers(owner_b),
        json={
            "membership_id": membership_id,
            "branch_id": other_branch_response.json()["id"],
            "effective_from": "2026-08-20",
            "reason": "Must never cross tenant boundary",
        },
    )
    assert cross_tenant_assignment.status_code == 404

    archived = await db_client.delete(
        f"/api/v1/branches/{first_branch['id']}?version=1",
        headers=headers(owner_a),
    )
    assert archived.status_code == 204
    active = await db_client.get("/api/v1/branches", headers=headers(owner_a))
    assert active.json()["total"] == 1
