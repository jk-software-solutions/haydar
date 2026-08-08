from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import httpx


def auth_headers(session: dict[str, Any], installation_id: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    if installation_id:
        headers["X-Installation-ID"] = installation_id
    return headers


async def register_company(client: httpx.AsyncClient, name: str, email: str) -> dict[str, Any]:
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


async def invite_employee(
    client: httpx.AsyncClient, owner: dict[str, Any], email: str
) -> dict[str, Any]:
    invitation = await client.post(
        "/api/v1/invitations",
        headers=auth_headers(owner),
        json={"email": email, "full_name": "Operations Employee", "role_code": "EMPLOYEE"},
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


async def configure_attendance(
    client: httpx.AsyncClient, owner: dict[str, Any], employee: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    today = date.today()
    branch_response = await client.post(
        "/api/v1/branches",
        headers=auth_headers(owner),
        json={
            "code": "OPS",
            "name": "Operations",
            "full_address": "Riyadh",
            "latitude": "24.713600",
            "longitude": "46.675300",
            "geofence_radius_m": 150,
            "timezone": "Asia/Riyadh",
            "working_hours": {},
        },
    )
    assert branch_response.status_code == 201
    branch = branch_response.json()
    membership_id = employee["session"]["membership_id"]
    branch_assignment = await client.post(
        "/api/v1/branches/assignments",
        headers=auth_headers(owner),
        json={
            "membership_id": membership_id,
            "branch_id": branch["id"],
            "effective_from": (today - timedelta(days=1)).isoformat(),
            "reason": "Attendance test assignment",
        },
    )
    assert branch_assignment.status_code == 201
    shift_response = await client.post(
        "/api/v1/shifts",
        headers=auth_headers(owner),
        json={
            "code": "ALLDAYS",
            "name": "All-days shift",
            "start_time": "00:00:00",
            "end_time": "23:59:00",
            "working_days": [0, 1, 2, 3, 4, 5, 6],
            "grace_period_minutes": 10,
            "break_duration_minutes": 0,
            "effective_from": (today - timedelta(days=1)).isoformat(),
            "effective_to": (today + timedelta(days=30)).isoformat(),
            "recurrence": {"frequency": "weekly"},
        },
    )
    assert shift_response.status_code == 201
    shift = shift_response.json()
    shift_assignment = await client.post(
        "/api/v1/shifts/assignments",
        headers=auth_headers(owner),
        json={
            "shift_id": shift["id"],
            "membership_id": membership_id,
            "effective_from": (today - timedelta(days=1)).isoformat(),
            "effective_to": (today + timedelta(days=30)).isoformat(),
        },
    )
    assert shift_assignment.status_code == 201
    return branch, shift


async def test_attendance_requires_approved_device_and_tracks_session(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(db_client, "Attendance Ops", "attendance-ops@example.com")
    employee = await invite_employee(db_client, owner, "attendance-worker@example.com")
    await configure_attendance(db_client, owner, employee)
    action = {"method": "gps", "latitude": "24.713600", "longitude": "46.675300"}

    missing_device = await db_client.post(
        "/api/v1/attendance/check-in", headers=auth_headers(employee), json=action
    )
    assert missing_device.status_code == 400
    assert missing_device.json()["code"] == "installation_id_required"

    installation_id = str(uuid4())
    registration = await db_client.post(
        "/api/v1/devices/register",
        headers=auth_headers(employee),
        json={
            "installation_id": installation_id,
            "platform": "android",
            "device_name": "Attendance phone",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["device"]["status"] == "approved"

    check_in = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json=action,
    )
    assert check_in.status_code == 201
    assert check_in.json()["checked_in_at"] is not None
    duplicate = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json=action,
    )
    assert duplicate.status_code == 409

    check_out = await db_client.post(
        "/api/v1/attendance/check-out",
        headers=auth_headers(employee, installation_id),
        json=action,
    )
    assert check_out.status_code == 200
    assert check_out.json()["checked_out_at"] is not None
    history = await db_client.get("/api/v1/attendance/me", headers=auth_headers(employee))
    assert history.status_code == 200
    assert len(history.json()) == 1


async def test_tasks_leave_files_exports_and_tenant_isolation(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(db_client, "Workforce Ops", "workforce-ops@example.com")
    other_owner = await register_company(db_client, "Other Ops", "other-ops@example.com")
    employee = await invite_employee(db_client, owner, "workforce-worker@example.com")
    membership_id = employee["session"]["membership_id"]

    plans = await db_client.get("/api/v1/billing/plans")
    subscription = await db_client.get("/api/v1/billing/subscription", headers=auth_headers(owner))
    assert plans.status_code == 200
    assert {plan["code"] for plan in plans.json()} == {
        "FREE_TRIAL",
        "BASIC",
        "PROFESSIONAL",
        "ENTERPRISE",
    }
    assert subscription.status_code == 200
    assert subscription.json()["plan"]["code"] == "FREE_TRIAL"

    task = await db_client.post(
        "/api/v1/tasks",
        headers=auth_headers(owner),
        json={
            "title": "Verify site readiness",
            "description": "Complete the assigned operational checklist.",
            "priority": "urgent",
            "membership_ids": [membership_id],
        },
    )
    assert task.status_code == 201
    task_id = task.json()["id"]
    employee_tasks = await db_client.get("/api/v1/tasks", headers=auth_headers(employee))
    assert employee_tasks.status_code == 200
    assert [item["id"] for item in employee_tasks.json()] == [task_id]
    status_update = await db_client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers(employee),
        json={"version": 1, "status": "in_progress"},
    )
    assert status_update.status_code == 200
    notifications = await db_client.get(
        "/api/v1/notifications?unread_only=true", headers=auth_headers(owner)
    )
    assert notifications.status_code == 200
    assert any(item["kind"] == "task_status_changed" for item in notifications.json())

    leave_type = await db_client.post(
        "/api/v1/leave/types",
        headers=auth_headers(owner),
        json={"code": "ANNUAL", "name": "Annual leave", "default_days": 20},
    )
    assert leave_type.status_code == 201
    leave_type_id = leave_type.json()["id"]
    balance = await db_client.put(
        "/api/v1/leave/balances",
        headers=auth_headers(owner),
        json={
            "membership_id": membership_id,
            "leave_type_id": leave_type_id,
            "year": 2026,
            "allocated_days": 20,
            "reason": "Annual allocation",
        },
    )
    assert balance.status_code == 200
    leave = await db_client.post(
        "/api/v1/leave/requests",
        headers=auth_headers(employee),
        json={
            "leave_type_id": leave_type_id,
            "starts_on": "2026-09-01",
            "ends_on": "2026-09-02",
            "reason": "Family commitment",
        },
    )
    assert leave.status_code == 201
    review = await db_client.post(
        f"/api/v1/leave/requests/{leave.json()['id']}/review",
        headers=auth_headers(owner),
        json={"decision": "approved", "comment": "Approved"},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "approved"

    upload = await db_client.post(
        "/api/v1/files",
        headers=auth_headers(employee),
        files={"upload": ("note.txt", b"tenant protected", "text/plain")},
    )
    assert upload.status_code == 201
    file_id = upload.json()["id"]
    own_download = await db_client.get(f"/api/v1/files/{file_id}", headers=auth_headers(employee))
    assert own_download.status_code == 200
    assert own_download.content == b"tenant protected"
    cross_tenant_download = await db_client.get(
        f"/api/v1/files/{file_id}", headers=auth_headers(other_owner)
    )
    assert cross_tenant_download.status_code == 404

    export = await db_client.post(
        "/api/v1/reports/exports",
        headers=auth_headers(owner),
        json={"report_type": "tasks", "export_format": "xlsx", "locale": "en"},
    )
    assert export.status_code == 201
    assert export.json()["status"] == "completed"
    download = await db_client.get(
        f"/api/v1/reports/exports/{export.json()['id']}/download",
        headers=auth_headers(owner),
    )
    assert download.status_code == 200
    assert download.content.startswith(b"PK")
