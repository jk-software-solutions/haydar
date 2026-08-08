import httpx


def headers(session: dict[str, object]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def register_company(client: httpx.AsyncClient, name: str, email: str) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register-company",
        json={
            "company_name": name,
            "owner_full_name": f"Owner {name}",
            "owner_email": email,
            "password": "ChangeMe123!",
        },
    )
    assert response.status_code == 201
    return response.json()


async def invite_and_activate_manager(
    client: httpx.AsyncClient, owner: dict[str, object]
) -> dict[str, object]:
    invitation = await client.post(
        "/api/v1/invitations",
        headers=headers(owner),
        json={
            "email": "scoped-manager@example.com",
            "full_name": "Scoped Manager",
            "role_code": "MANAGER",
        },
    )
    assert invitation.status_code == 201
    activation = await client.post(
        "/api/v1/auth/invitations/activate",
        json={
            "activation_token": invitation.json()["activation_token"],
            "password": "ManagerPass123!",
        },
    )
    assert activation.status_code == 200
    return activation.json()


async def test_owner_assigns_granular_permissions_and_tenant_safe_scopes(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(db_client, "Scoped Access", "access-owner@example.com")
    other_owner = await register_company(
        db_client, "Other Access", "other-access-owner@example.com"
    )
    manager = await invite_and_activate_manager(db_client, owner)
    branch = await db_client.post(
        "/api/v1/branches",
        headers=headers(owner),
        json={
            "code": "SCOPE-1",
            "name": "Scoped Branch",
            "full_address": "Riyadh",
            "latitude": "24.713600",
            "longitude": "46.675300",
            "geofence_radius_m": 100,
            "timezone": "Asia/Riyadh",
            "working_hours": {},
        },
    )
    other_branch = await db_client.post(
        "/api/v1/branches",
        headers=headers(owner),
        json={
            "code": "SCOPE-2",
            "name": "Hidden Branch",
            "full_address": "Jeddah",
            "latitude": "21.485800",
            "longitude": "39.192500",
            "geofence_radius_m": 100,
            "timezone": "Asia/Riyadh",
            "working_hours": {},
        },
    )
    department = await db_client.post(
        "/api/v1/departments",
        headers=headers(owner),
        json={"code": "FIELD", "name": "Field"},
    )
    group = await db_client.post(
        "/api/v1/groups",
        headers=headers(owner),
        json={"code": "NORTH", "name": "North Team", "description": "North region"},
    )
    assert branch.status_code == other_branch.status_code == department.status_code == 201
    assert group.status_code == 201
    membership_id = manager["session"]["membership_id"]

    updated = await db_client.put(
        f"/api/v1/members/{membership_id}/access",
        headers=headers(owner),
        json={
            "role_codes": ["MANAGER"],
            "permission_overrides": {
                "branches:manage": False,
                "reports:view": True,
            },
            "branch_ids": [branch.json()["id"]],
            "department_ids": [department.json()["id"]],
            "group_ids": [group.json()["id"]],
        },
    )
    assert updated.status_code == 200
    access = updated.json()
    assert access["permission_overrides"]["branches:manage"] is False
    assert "branches:manage" not in access["effective_permissions"]
    assert access["branch_ids"] == [branch.json()["id"]]
    assert access["department_ids"] == [department.json()["id"]]
    assert access["group_ids"] == [group.json()["id"]]

    refreshed_session = await db_client.get("/api/v1/auth/session", headers=headers(manager))
    assert refreshed_session.status_code == 200
    assert "branches:manage" not in refreshed_session.json()["permissions"]
    assert refreshed_session.json()["scope"]["unrestricted"] is False
    assert refreshed_session.json()["scope"]["group_ids"] == [group.json()["id"]]

    scoped_branches = await db_client.get("/api/v1/branches", headers=headers(manager))
    assert scoped_branches.status_code == 200
    assert [item["id"] for item in scoped_branches.json()["items"]] == [branch.json()["id"]]
    hidden_branch = await db_client.get(
        f"/api/v1/branches/{other_branch.json()['id']}", headers=headers(manager)
    )
    assert hidden_branch.status_code == 404

    forbidden_create = await db_client.post(
        "/api/v1/branches",
        headers=headers(manager),
        json={
            "code": "DENIED",
            "name": "Denied Branch",
            "full_address": "Riyadh",
            "latitude": "24.713600",
            "longitude": "46.675300",
            "geofence_radius_m": 100,
            "timezone": "Asia/Riyadh",
            "working_hours": {},
        },
    )
    assert forbidden_create.status_code == 403

    cross_tenant_update = await db_client.put(
        f"/api/v1/members/{membership_id}/access",
        headers=headers(other_owner),
        json={
            "role_codes": ["MANAGER"],
            "permission_overrides": {},
            "branch_ids": [],
            "department_ids": [],
            "group_ids": [],
        },
    )
    assert cross_tenant_update.status_code == 404

    manager_catalog = await db_client.get(
        "/api/v1/members/access-catalog", headers=headers(manager)
    )
    assert manager_catalog.status_code == 403


async def test_group_membership_rejects_cross_tenant_members(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(db_client, "Groups A", "groups-a@example.com")
    other_owner = await register_company(db_client, "Groups B", "groups-b@example.com")
    group = await db_client.post(
        "/api/v1/groups",
        headers=headers(owner),
        json={"code": "OPS", "name": "Operations"},
    )
    assert group.status_code == 201
    cross_tenant = await db_client.put(
        f"/api/v1/groups/{group.json()['id']}/members",
        headers=headers(owner),
        json={"membership_ids": [other_owner["session"]["membership_id"]]},
    )
    assert cross_tenant.status_code == 404

    own_update = await db_client.put(
        f"/api/v1/groups/{group.json()['id']}/members",
        headers=headers(owner),
        json={"membership_ids": [owner["session"]["membership_id"]]},
    )
    assert own_update.status_code == 200
    assert own_update.json()["membership_ids"] == [owner["session"]["membership_id"]]
