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


async def invite_employee(client: httpx.AsyncClient, owner: dict[str, object]) -> dict[str, object]:
    invitation = await client.post(
        "/api/v1/invitations",
        headers=headers(owner),
        json={
            "email": "shift-employee@example.com",
            "full_name": "Shift Employee",
            "role_code": "EMPLOYEE",
        },
    )
    activation = await client.post(
        "/api/v1/auth/invitations/activate",
        json={
            "activation_token": invitation.json()["activation_token"],
            "password": "EmployeePass123!",
        },
    )
    assert activation.status_code == 200
    return activation.json()


def shift_payload(code: str, start: str, end: str) -> dict[str, object]:
    return {
        "code": code,
        "name": f"{code} Shift",
        "start_time": start,
        "end_time": end,
        "working_days": [0, 1, 2, 3, 4],
        "grace_period_minutes": 10,
        "break_duration_minutes": 60,
        "effective_from": "2026-08-01",
        "effective_to": "2026-12-31",
        "recurrence": {"frequency": "weekly"},
    }


async def test_overnight_shift_assignment_conflicts_and_tenant_isolation(
    db_client: httpx.AsyncClient,
) -> None:
    owner_a = await register_company(db_client, "Shifts A", "shifts-a@example.com")
    owner_b = await register_company(db_client, "Shifts B", "shifts-b@example.com")
    employee = await invite_employee(db_client, owner_a)
    membership_id = employee["session"]["membership_id"]

    overnight = await db_client.post(
        "/api/v1/shifts",
        headers=headers(owner_a),
        json=shift_payload("NIGHT", "22:00:00", "06:00:00"),
    )
    assert overnight.status_code == 201
    shift = overnight.json()
    assert shift["is_overnight"] is True

    employee_list = await db_client.get("/api/v1/shifts", headers=headers(employee))
    assert employee_list.status_code == 200
    assert employee_list.json()["total"] == 1

    other_list = await db_client.get("/api/v1/shifts", headers=headers(owner_b))
    assert other_list.status_code == 200
    assert other_list.json()["items"] == []

    cross_tenant = await db_client.get(f"/api/v1/shifts/{shift['id']}", headers=headers(owner_b))
    assert cross_tenant.status_code == 404

    rejected_company_id = await db_client.post(
        "/api/v1/shifts",
        headers=headers(owner_a),
        json={
            **shift_payload("BAD", "08:00:00", "17:00:00"),
            "company_id": owner_b["session"]["company"]["id"],
        },
    )
    assert rejected_company_id.status_code == 422

    assignment = await db_client.post(
        "/api/v1/shifts/assignments",
        headers=headers(owner_a),
        json={
            "shift_id": shift["id"],
            "membership_id": membership_id,
            "effective_from": "2026-08-01",
            "effective_to": "2026-10-31",
        },
    )
    assert assignment.status_code == 201

    overlapping = await db_client.post(
        "/api/v1/shifts/assignments",
        headers=headers(owner_a),
        json={
            "shift_id": shift["id"],
            "membership_id": membership_id,
            "effective_from": "2026-10-01",
            "effective_to": "2026-12-01",
        },
    )
    assert overlapping.status_code == 409
    assert overlapping.json()["code"] == "shift_assignment_overlap"

    own_assignments = await db_client.get(
        "/api/v1/shifts/assignments/me", headers=headers(employee)
    )
    assert own_assignments.status_code == 200
    assert own_assignments.json()[0]["shift_code"] == "NIGHT"

    exception = await db_client.post(
        f"/api/v1/shifts/{shift['id']}/exceptions",
        headers=headers(owner_a),
        json={
            "exception_date": "2026-09-23",
            "is_working_day": False,
            "note": "National Day",
        },
    )
    assert exception.status_code == 201

    updated = await db_client.patch(
        f"/api/v1/shifts/{shift['id']}",
        headers=headers(owner_a),
        json={"version": 1, "start_time": "08:00:00", "end_time": "17:00:00"},
    )
    assert updated.status_code == 200
    assert updated.json()["is_overnight"] is False

    stale = await db_client.patch(
        f"/api/v1/shifts/{shift['id']}",
        headers=headers(owner_a),
        json={"version": 1, "name": "Stale"},
    )
    assert stale.status_code == 409

    cross_tenant_assignment = await db_client.post(
        "/api/v1/shifts/assignments",
        headers=headers(owner_b),
        json={
            "shift_id": shift["id"],
            "membership_id": owner_b["session"]["membership_id"],
            "effective_from": "2026-08-01",
        },
    )
    assert cross_tenant_assignment.status_code == 404
