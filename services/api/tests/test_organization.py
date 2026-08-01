import httpx


async def register_company(
    client: httpx.AsyncClient,
    *,
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
    *,
    email: str,
) -> dict[str, object]:
    invitation = await client.post(
        "/api/v1/invitations",
        headers=headers(owner),
        json={
            "email": email,
            "full_name": "Tenant Employee",
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


async def test_employee_profiles_are_tenant_scoped_and_versioned(
    db_client: httpx.AsyncClient,
) -> None:
    owner_a = await register_company(
        db_client,
        company_name="Profiles A",
        email="profiles-owner-a@example.com",
    )
    owner_b = await register_company(
        db_client,
        company_name="Profiles B",
        email="profiles-owner-b@example.com",
    )
    employee = await invite_employee(
        db_client,
        owner_a,
        email="tenant-employee@example.com",
    )

    own_profile = await db_client.get("/api/v1/employees/me", headers=headers(employee))
    assert own_profile.status_code == 200
    employee_profile = own_profile.json()
    assert employee_profile["display_name"] == "Tenant Employee"
    assert employee_profile["role_code"] == "EMPLOYEE"

    company_list = await db_client.get("/api/v1/employees", headers=headers(owner_a))
    other_list = await db_client.get("/api/v1/employees", headers=headers(owner_b))
    assert company_list.status_code == 200
    assert company_list.json()["total"] == 2
    assert other_list.status_code == 200
    assert other_list.json()["total"] == 1

    employee_list = await db_client.get("/api/v1/employees", headers=headers(employee))
    assert employee_list.status_code == 403
    assert employee_list.json()["code"] == "permission_denied"

    membership_id = employee_profile["membership_id"]
    cross_tenant = await db_client.get(
        f"/api/v1/employees/{membership_id}",
        headers=headers(owner_b),
    )
    assert cross_tenant.status_code == 404
    assert cross_tenant.json()["code"] == "employee_not_found"

    update = await db_client.patch(
        f"/api/v1/employees/{membership_id}",
        headers=headers(owner_a),
        json={
            "version": employee_profile["version"],
            "employee_number": "EMP-1001",
            "job_title": "Field specialist",
            "phone": "+966500000001",
        },
    )
    assert update.status_code == 200
    assert update.json()["version"] == 2
    assert update.json()["employee_number"] == "EMP-1001"

    stale_update = await db_client.patch(
        f"/api/v1/employees/{membership_id}",
        headers=headers(owner_a),
        json={"version": 1, "job_title": "Stale title"},
    )
    assert stale_update.status_code == 409
    assert stale_update.json()["code"] == "concurrency_conflict"

    cross_tenant_update = await db_client.patch(
        f"/api/v1/employees/{membership_id}",
        headers=headers(owner_b),
        json={"version": 2, "job_title": "Wrong tenant"},
    )
    assert cross_tenant_update.status_code == 404

    rejected_company_id = await db_client.patch(
        f"/api/v1/employees/{membership_id}",
        headers=headers(owner_a),
        json={
            "version": 2,
            "company_id": owner_b["session"]["company"]["id"],
        },
    )
    assert rejected_company_id.status_code == 422

    rejected_null = await db_client.patch(
        f"/api/v1/employees/{membership_id}",
        headers=headers(owner_a),
        json={"version": 2, "display_name": None},
    )
    assert rejected_null.status_code == 422


async def test_company_settings_use_session_tenant_and_owner_permission(
    db_client: httpx.AsyncClient,
) -> None:
    owner_a = await register_company(
        db_client,
        company_name="Settings A",
        email="settings-owner-a@example.com",
    )
    owner_b = await register_company(
        db_client,
        company_name="Settings B",
        email="settings-owner-b@example.com",
    )
    employee = await invite_employee(
        db_client,
        owner_a,
        email="settings-employee@example.com",
    )

    initial = await db_client.get("/api/v1/companies/current", headers=headers(owner_a))
    assert initial.status_code == 200
    assert initial.json()["default_locale"] == "ar"

    update = await db_client.patch(
        "/api/v1/companies/current",
        headers=headers(owner_a),
        json={
            "version": initial.json()["version"],
            "display_name": "Settings A Updated",
            "default_locale": "en",
            "timezone": "Asia/Riyadh",
            "country_code": "sa",
        },
    )
    assert update.status_code == 200
    assert update.json()["country_code"] == "SA"
    assert update.json()["version"] == initial.json()["version"] + 1

    other = await db_client.get("/api/v1/companies/current", headers=headers(owner_b))
    assert other.status_code == 200
    assert other.json()["display_name"] == "Settings B"

    forbidden = await db_client.patch(
        "/api/v1/companies/current",
        headers=headers(employee),
        json={"version": update.json()["version"], "display_name": "Forbidden"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "permission_denied"

    rejected_null = await db_client.patch(
        "/api/v1/companies/current",
        headers=headers(owner_a),
        json={"version": update.json()["version"], "timezone": None},
    )
    assert rejected_null.status_code == 422
