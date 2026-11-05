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
            "owner_full_name": f"Owner of {company_name}",
            "owner_email": email,
            "password": "ChangeMe123!",
        },
    )
    assert response.status_code == 201
    return response.json()


def auth_headers(payload: dict[str, object]) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


async def test_invitation_activation_and_tenant_isolation(
    db_client: httpx.AsyncClient,
) -> None:
    company_a = await register_company(
        db_client,
        company_name="Company A",
        email="owner-a@example.com",
    )
    company_b = await register_company(
        db_client,
        company_name="Company B",
        email="owner-b@example.com",
    )

    create_response = await db_client.post(
        "/api/v1/invitations",
        headers=auth_headers(company_a),
        json={
            "email": "employee-a@example.com",
            "full_name": "Employee A",
            "role_code": "EMPLOYEE",
        },
    )
    assert create_response.status_code == 201
    invitation = create_response.json()
    assert invitation["activation_token"]

    own_list = await db_client.get(
        "/api/v1/invitations",
        headers=auth_headers(company_a),
    )
    other_list = await db_client.get(
        "/api/v1/invitations",
        headers=auth_headers(company_b),
    )
    assert [item["id"] for item in own_list.json()["items"]] == [invitation["id"]]
    assert own_list.json()["total"] == 1
    assert other_list.json()["items"] == []
    assert other_list.json()["total"] == 0

    cross_tenant_read = await db_client.get(
        f"/api/v1/invitations/{invitation['id']}",
        headers=auth_headers(company_b),
    )
    assert cross_tenant_read.status_code == 404
    assert cross_tenant_read.json()["code"] == "invitation_not_found"

    resend_response = await db_client.post(
        f"/api/v1/invitations/{invitation['id']}/resend-code",
        headers=auth_headers(company_a),
    )
    assert resend_response.status_code == 200
    resent_invitation = resend_response.json()
    assert resent_invitation["activation_token"]
    assert resent_invitation["activation_token"] != invitation["activation_token"]

    old_activation = await db_client.post(
        "/api/v1/auth/invitations/activate",
        json={
            "activation_token": invitation["activation_token"],
            "password": "EmployeePass123!",
        },
    )
    assert old_activation.status_code == 400

    activation = await db_client.post(
        "/api/v1/auth/invitations/activate",
        json={
            "activation_token": resent_invitation["activation_token"],
            "password": "EmployeePass123!",
        },
    )
    assert activation.status_code == 200
    employee_session = activation.json()
    assert employee_session["session"]["roles"] == ["EMPLOYEE"]
    assert employee_session["session"]["company"]["id"] == company_a["session"]["company"]["id"]

    forbidden_invite = await db_client.post(
        "/api/v1/invitations",
        headers=auth_headers(employee_session),
        json={
            "email": "another@example.com",
            "full_name": "Another Employee",
            "role_code": "EMPLOYEE",
        },
    )
    assert forbidden_invite.status_code == 403
    assert forbidden_invite.json()["code"] == "permission_denied"

    reused_activation = await db_client.post(
        "/api/v1/auth/invitations/activate",
        json={
            "activation_token": resent_invitation["activation_token"],
            "password": "EmployeePass123!",
        },
    )
    assert reused_activation.status_code == 400


async def test_invitation_rejects_client_supplied_company_id(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(
        db_client,
        company_name="Scoped Company",
        email="scoped-owner@example.com",
    )
    response = await db_client.post(
        "/api/v1/invitations",
        headers=auth_headers(owner),
        json={
            "company_id": "00000000-0000-0000-0000-000000000000",
            "email": "employee@example.com",
            "full_name": "Employee",
            "role_code": "EMPLOYEE",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
