from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.jobs.maintenance import expire_presence_requests
from app.models.attendance import PresenceRequest
from app.models.platform import ExportJob


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
    client: httpx.AsyncClient,
    owner: dict[str, Any],
    employee: dict[str, Any],
    recurrence: dict[str, Any] | None = None,
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
            "recurrence": recurrence or {"frequency": "weekly"},
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


async def test_locationless_shift_allows_gps_outside_branch_geofence(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(db_client, "Locationless Ops", "locationless@example.com")
    employee = await invite_employee(db_client, owner, "locationless-worker@example.com")
    branch, _shift = await configure_attendance(
        db_client,
        owner,
        employee,
        recurrence={
            "frequency": "weekly",
            "location_policy": "location_not_required",
            "periods": [{"start_time": "00:00:00", "end_time": "23:59:00"}],
        },
    )
    installation_id = str(uuid4())
    registration = await db_client.post(
        "/api/v1/devices/register",
        headers=auth_headers(employee),
        json={
            "installation_id": installation_id,
            "platform": "android",
            "device_name": "Remote attendance phone",
        },
    )
    assert registration.status_code == 201

    check_in = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json={
            "method": "gps",
            "latitude": "21.543333",
            "longitude": "39.172778",
        },
    )

    assert branch["geofence_radius_m"] == 150
    assert check_in.status_code == 201
    assert check_in.json()["checked_in_at"] is not None
    location_events = await db_client.get(
        f"/api/v1/attendance/records/{check_in.json()['id']}/location-events",
        headers=auth_headers(owner),
    )
    assert location_events.status_code == 200
    assert location_events.json()[0]["method"] == "gps"
    assert location_events.json()[0]["latitude"] == "21.543333"


async def test_attendance_requires_approved_device_and_tracks_session(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(db_client, "Attendance Ops", "attendance-ops@example.com")
    employee = await invite_employee(db_client, owner, "attendance-worker@example.com")
    branch, _shift = await configure_attendance(db_client, owner, employee)
    qr_response = await db_client.post(
        "/api/v1/attendance/qr-tokens",
        headers=auth_headers(owner),
        json={"branch_id": branch["id"], "valid_for_seconds": 900},
    )
    assert qr_response.status_code == 201
    action = {
        "method": "qr",
        "latitude": "24.713600",
        "longitude": "46.675300",
        "qr_token": qr_response.json()["token"],
    }

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

    required_biometric = await db_client.patch(
        "/api/v1/companies/current",
        headers=auth_headers(owner),
        json={"version": 1, "attendance_biometric_policy": "required"},
    )
    assert required_biometric.status_code == 200
    required_rejection = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json=action,
    )
    assert required_rejection.status_code == 403
    assert required_rejection.json()["code"] == "biometric_confirmation_required"
    optional_biometric = await db_client.patch(
        "/api/v1/companies/current",
        headers=auth_headers(owner),
        json={"version": 2, "attendance_biometric_policy": "optional"},
    )
    assert optional_biometric.status_code == 200

    presence_group = await db_client.post(
        "/api/v1/groups",
        headers=auth_headers(owner),
        json={"code": "PRESENCE", "name": "Presence Team"},
    )
    assert presence_group.status_code == 201
    presence_members = await db_client.put(
        f"/api/v1/groups/{presence_group.json()['id']}/members",
        headers=auth_headers(owner),
        json={"membership_ids": [employee["session"]["membership_id"]]},
    )
    assert presence_members.status_code == 200
    group_challenge = await db_client.post(
        "/api/v1/presence-requests",
        headers=auth_headers(owner),
        json={
            "group_id": presence_group.json()["id"],
            "message": "Confirm group presence",
            "deadline_seconds": 300,
        },
    )
    assert group_challenge.status_code == 201
    assert len(group_challenge.json()) == 1
    presence_response = await db_client.post(
        f"/api/v1/presence-requests/{group_challenge.json()[0]['request_id']}/respond",
        headers=auth_headers(employee, installation_id),
        json={"latitude": "24.713600", "longitude": "46.675300"},
    )
    assert presence_response.status_code == 200
    assert presence_response.json()["status"] == "verified"
    timeout_challenge = await db_client.post(
        "/api/v1/presence-requests",
        headers=auth_headers(owner),
        json={
            "membership_ids": [employee["session"]["membership_id"]],
            "message": "Timeout coverage",
            "deadline_seconds": 30,
        },
    )
    assert timeout_challenge.status_code == 201
    settings = get_settings()
    assert settings.test_database_url is not None
    presence_engine = create_async_engine(settings.test_database_url)
    presence_sessions = async_sessionmaker(presence_engine, expire_on_commit=False)
    async with presence_sessions() as presence_session:
        await presence_session.execute(
            update(PresenceRequest)
            .where(PresenceRequest.id == UUID(timeout_challenge.json()[0]["request_id"]))
            .values(deadline_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        assert await expire_presence_requests(presence_session, datetime.now(UTC)) == 1
        await presence_session.commit()
    await presence_engine.dispose()
    presence_results = await db_client.get(
        "/api/v1/presence-requests", headers=auth_headers(owner)
    )
    assert presence_results.status_code == 200
    statuses = {item["request_id"]: item["status"] for item in presence_results.json()}
    assert statuses[group_challenge.json()[0]["request_id"]] == "verified"
    assert statuses[timeout_challenge.json()[0]["request_id"]] == "no_response"

    rotated = await db_client.post(
        "/api/v1/attendance/qr-tokens/rotate",
        headers=auth_headers(owner),
        json={"branch_id": branch["id"], "valid_for_seconds": 900},
    )
    assert rotated.status_code == 201
    invalidated_previous = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json=action,
    )
    assert invalidated_previous.status_code == 403
    assert invalidated_previous.json()["code"] == "qr_token_invalid"
    action["qr_token"] = rotated.json()["token"]
    revocable = await db_client.post(
        "/api/v1/attendance/qr-tokens",
        headers=auth_headers(owner),
        json={"branch_id": branch["id"], "valid_for_seconds": 900},
    )
    assert revocable.status_code == 201
    revoked = await db_client.delete(
        f"/api/v1/attendance/qr-tokens/{revocable.json()['id']}",
        headers=auth_headers(owner),
    )
    assert revoked.status_code == 204
    revoked_attempt = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json={**action, "qr_token": revocable.json()["token"]},
    )
    assert revoked_attempt.status_code == 403
    active_tokens = await db_client.get(
        f"/api/v1/attendance/qr-tokens?branch_id={branch['id']}",
        headers=auth_headers(owner),
    )
    assert active_tokens.status_code == 200
    assert [item["id"] for item in active_tokens.json()] == [rotated.json()["id"]]
    other_branch = await db_client.post(
        "/api/v1/branches",
        headers=auth_headers(owner),
        json={
            "code": "OTHER",
            "name": "Other Branch",
            "full_address": "Jeddah",
            "latitude": "24.713600",
            "longitude": "46.675300",
            "geofence_radius_m": 150,
            "timezone": "Asia/Riyadh",
            "working_hours": {},
        },
    )
    assert other_branch.status_code == 201
    wrong_branch_qr = await db_client.post(
        "/api/v1/attendance/qr-tokens",
        headers=auth_headers(owner),
        json={"branch_id": other_branch.json()["id"], "valid_for_seconds": 900},
    )
    assert wrong_branch_qr.status_code == 201
    wrong_branch_attempt = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json={**action, "qr_token": wrong_branch_qr.json()["token"]},
    )
    assert wrong_branch_attempt.status_code == 403
    assert wrong_branch_attempt.json()["code"] == "qr_token_invalid"

    check_in_headers = {
        **auth_headers(employee, installation_id),
        "Idempotency-Key": "attendance-check-in-001",
    }
    check_in = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=check_in_headers,
        json=action,
    )
    assert check_in.status_code == 201
    assert check_in.json()["checked_in_at"] is not None
    repeated_check_in = await db_client.post(
        "/api/v1/attendance/check-in", headers=check_in_headers, json=action
    )
    assert repeated_check_in.status_code == 201
    assert repeated_check_in.json() == check_in.json()
    conflicting_check_in = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=check_in_headers,
        json={**action, "latitude": "24.713700"},
    )
    assert conflicting_check_in.status_code == 409
    assert conflicting_check_in.json()["code"] == "idempotency_key_conflict"
    duplicate = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json=action,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "qr_token_replayed"

    early_check_out = await db_client.post(
        "/api/v1/attendance/check-out",
        headers=auth_headers(employee, installation_id),
        json=action,
    )
    assert early_check_out.status_code == 409
    assert early_check_out.json()["code"] == "checkout_too_early"

    permission_start = datetime.now(UTC) - timedelta(minutes=1)
    permission = await db_client.post(
        "/api/v1/permission-requests",
        headers=auth_headers(employee),
        json={
            "request_type": "one_hour",
            "starts_at": permission_start.isoformat(),
            "ends_at": (permission_start + timedelta(hours=1)).isoformat(),
            "reason": "Approved early departure test",
        },
    )
    assert permission.status_code == 201
    permission_approval = await db_client.post(
        f"/api/v1/permission-requests/{permission.json()['id']}/review",
        headers=auth_headers(owner),
        json={"decision": "approved", "comment": "Approved for test"},
    )
    assert permission_approval.status_code == 200

    check_out = await db_client.post(
        "/api/v1/attendance/check-out",
        headers={
            **auth_headers(employee, installation_id),
            "Idempotency-Key": "attendance-check-out-001",
        },
        json=action,
    )
    assert check_out.status_code == 200
    assert check_out.json()["checked_out_at"] is not None
    history = await db_client.get("/api/v1/attendance/me", headers=auth_headers(employee))
    assert history.status_code == 200
    assert len(history.json()) == 1


async def test_geofence_exit_detection_permission_reconfirmation_and_review(
    db_client: httpx.AsyncClient, monkeypatch: Any
) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "geofence_exit_grace_seconds", 0)
    monkeypatch.setattr(settings, "geofence_exit_min_samples", 2)

    owner = await register_company(db_client, "Exit Ops", "exit-ops@example.com")
    other_owner = await register_company(db_client, "Other Exit Ops", "other-exit@example.com")
    employee = await invite_employee(db_client, owner, "exit-worker@example.com")
    branch, _shift = await configure_attendance(db_client, owner, employee)
    installation_id = str(uuid4())
    registration = await db_client.post(
        "/api/v1/devices/register",
        headers=auth_headers(employee),
        json={
            "installation_id": installation_id,
            "platform": "android",
            "device_name": "Geofence phone",
        },
    )
    assert registration.status_code == 201
    check_in = await db_client.post(
        "/api/v1/attendance/check-in",
        headers=auth_headers(employee, installation_id),
        json={
            "method": "gps",
            "latitude": "24.713600",
            "longitude": "46.675300",
        },
    )
    assert check_in.status_code == 201
    record_id = check_in.json()["id"]

    first_time = datetime.now(UTC)
    outside_sample = {
        "record_id": record_id,
        "observed_at": first_time.isoformat(),
        "latitude": "24.730000",
        "longitude": "46.690000",
        "accuracy_m": 12,
        "source": "foreground_monitor",
        "location_permission": "while_in_use",
    }
    first = await db_client.post(
        "/api/v1/geofence-exit-events/report",
        headers=auth_headers(employee, installation_id),
        json=outside_sample,
    )
    assert first.status_code == 201
    assert first.json()["status"] == "observing"
    assert first.json()["consecutive_outside_samples"] == 1

    outside_sample["observed_at"] = (first_time + timedelta(seconds=1)).isoformat()
    second = await db_client.post(
        "/api/v1/geofence-exit-events/report",
        headers=auth_headers(employee, installation_id),
        json=outside_sample,
    )
    assert second.status_code == 201
    assert second.json()["status"] == "unauthorized"
    assert second.json()["consecutive_outside_samples"] == 2
    event_id = second.json()["id"]

    owner_notifications = await db_client.get(
        "/api/v1/notifications?unread_only=true", headers=auth_headers(owner)
    )
    assert owner_notifications.status_code == 200
    assert any(
        item["kind"] == "geofence_exit_unauthorized" and item["target_id"] == event_id
        for item in owner_notifications.json()
    )
    events = await db_client.get("/api/v1/geofence-exit-events", headers=auth_headers(owner))
    assert events.status_code == 200
    assert [event["id"] for event in events.json()] == [event_id]
    report = await db_client.get(
        "/api/v1/reports/geofence-exits?status=unauthorized",
        headers=auth_headers(owner),
    )
    assert report.status_code == 200
    assert report.json()["total"] == 1
    assert report.json()["status_counts"] == {"unauthorized": 1}
    other_events = await db_client.get(
        "/api/v1/geofence-exit-events", headers=auth_headers(other_owner)
    )
    assert other_events.status_code == 200
    assert other_events.json() == []

    inside = await db_client.post(
        "/api/v1/geofence-exit-events/report",
        headers=auth_headers(employee, installation_id),
        json={
            **outside_sample,
            "observed_at": (first_time + timedelta(seconds=2)).isoformat(),
            "latitude": "24.713600",
            "longitude": "46.675300",
        },
    )
    assert inside.status_code == 201
    assert inside.json()["reconfirmed_at"] is not None

    review_headers = {
        **auth_headers(owner),
        "Idempotency-Key": "geofence-review-001",
    }
    review_payload = {
        "decision": "confirmed_unauthorized",
        "comment": "Confirmed after manager review",
        "version": inside.json()["version"],
    }
    review = await db_client.post(
        f"/api/v1/geofence-exit-events/{event_id}/review",
        headers=review_headers,
        json=review_payload,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "confirmed_unauthorized"
    replayed_review = await db_client.post(
        f"/api/v1/geofence-exit-events/{event_id}/review",
        headers=review_headers,
        json=review_payload,
    )
    assert replayed_review.status_code == 200
    assert replayed_review.json() == review.json()
    cross_company_review = await db_client.post(
        f"/api/v1/geofence-exit-events/{event_id}/review",
        headers=auth_headers(other_owner),
        json={
            "decision": "dismissed",
            "comment": "Must not cross tenant boundary",
            "version": review.json()["version"],
        },
    )
    assert cross_company_review.status_code == 404

    permission_start = datetime.now(UTC) - timedelta(minutes=1)
    permission = await db_client.post(
        "/api/v1/permission-requests",
        headers=auth_headers(employee),
        json={
            "request_type": "one_hour",
            "starts_at": permission_start.isoformat(),
            "ends_at": (permission_start + timedelta(hours=1)).isoformat(),
            "reason": "Approved off-site work",
        },
    )
    assert permission.status_code == 201
    approval = await db_client.post(
        f"/api/v1/permission-requests/{permission.json()['id']}/review",
        headers=auth_headers(owner),
        json={"decision": "approved", "comment": "Approved"},
    )
    assert approval.status_code == 200
    approved_exit = await db_client.post(
        "/api/v1/geofence-exit-events/report",
        headers=auth_headers(employee, installation_id),
        json={**outside_sample, "observed_at": datetime.now(UTC).isoformat()},
    )
    assert approved_exit.status_code == 201
    assert approved_exit.json()["status"] == "approved_exit"
    assert approved_exit.json()["permission_request_id"] == permission.json()["id"]


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
    receipt_upload = await db_client.post(
        "/api/v1/files",
        headers=auth_headers(employee),
        files={"upload": ("completion-receipt.txt", b"receipt from employee", "text/plain")},
    )
    assert receipt_upload.status_code == 201
    receipt_file_id = receipt_upload.json()["id"]
    status_update = await db_client.post(
        f"/api/v1/tasks/{task_id}/status",
        headers=auth_headers(employee),
        json={
            "version": 1,
            "status": "in_progress",
            "completion_attachment_file_id": receipt_file_id,
        },
    )
    assert status_update.status_code == 200
    owner_receipt = await db_client.get(
        f"/api/v1/files/{receipt_file_id}", headers=auth_headers(owner)
    )
    assert owner_receipt.status_code == 200
    assert owner_receipt.content == b"receipt from employee"
    video_upload = await db_client.post(
        "/api/v1/files",
        headers=auth_headers(employee),
        files={"upload": ("receipt.mp4", b"not a real video", "image/png")},
    )
    assert video_upload.status_code == 415
    assert video_upload.json()["code"] == "video_upload_not_allowed"
    notifications = await db_client.get(
        "/api/v1/notifications?unread_only=true", headers=auth_headers(owner)
    )
    assert notifications.status_code == 200
    assert any(item["kind"] == "task_status_changed" for item in notifications.json())
    assert any(item["deep_link"].startswith("/app/tasks/") for item in notifications.json())
    unread_count = await db_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers(owner)
    )
    assert unread_count.status_code == 200
    assert unread_count.json()["unread_count"] >= 1
    default_preferences = await db_client.get(
        "/api/v1/notifications/preferences", headers=auth_headers(owner)
    )
    assert default_preferences.status_code == 200
    assert default_preferences.json()["push_enabled"] is True
    preferences = await db_client.put(
        "/api/v1/notifications/preferences",
        headers=auth_headers(owner),
        json={
            "in_app_enabled": True,
            "push_enabled": True,
            "email_enabled": False,
            "muted_kinds": ["task_due_soon", "task_due_soon"],
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "06:00",
        },
    )
    assert preferences.status_code == 200
    assert preferences.json()["muted_kinds"] == ["task_due_soon"]
    push_token = await db_client.post(
        "/api/v1/notifications/push-tokens",
        headers=auth_headers(owner),
        json={
            "token": "test-firebase-registration-token-00000001",
            "platform": "android",
            "app_version": "1.0.0",
        },
    )
    assert push_token.status_code == 200
    provider = await db_client.get(
        "/api/v1/notifications/provider-status", headers=auth_headers(owner)
    )
    assert provider.status_code == 200
    assert provider.json() == {
        "configured": False,
        "provider": "firebase_cloud_messaging",
    }
    cross_tenant_unregister = await db_client.delete(
        f"/api/v1/notifications/push-tokens/{push_token.json()['id']}",
        headers=auth_headers(other_owner),
    )
    assert cross_tenant_unregister.status_code == 404
    read_all = await db_client.post("/api/v1/notifications/read-all", headers=auth_headers(owner))
    assert read_all.status_code == 200
    assert read_all.json()["unread_count"] == 0

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

    yesterday = date.today() - timedelta(days=1)
    historical_leave = await db_client.post(
        "/api/v1/leave/requests",
        headers=auth_headers(employee),
        json={
            "leave_type_id": leave_type_id,
            "starts_on": yesterday.isoformat(),
            "ends_on": yesterday.isoformat(),
            "reason": "Approved historical leave",
        },
    )
    assert historical_leave.status_code == 201
    historical_review = await db_client.post(
        f"/api/v1/leave/requests/{historical_leave.json()['id']}/review",
        headers=auth_headers(owner),
        json={"decision": "approved", "comment": "Approved"},
    )
    assert historical_review.status_code == 200
    await configure_attendance(db_client, owner, employee)
    reconciliation = await db_client.post(
        f"/api/v1/attendance/reconcile?work_date={yesterday.isoformat()}",
        headers=auth_headers(owner),
    )
    assert reconciliation.status_code == 200
    assert reconciliation.json()["generated_absence_records"] == 1
    attendance = await db_client.get(
        "/api/v1/attendance",
        headers=auth_headers(owner),
        params={"membership_id": membership_id, "date_from": yesterday.isoformat()},
    )
    assert attendance.status_code == 200
    assert attendance.json()[0]["status"] == "on_leave"

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

    manager_upload = await db_client.post(
        "/api/v1/files",
        headers=auth_headers(owner),
        files={"upload": ("contract.pdf", b"protected contract", "application/pdf")},
    )
    assert manager_upload.status_code == 201
    manager_file_id = manager_upload.json()["id"]
    unlinked_download = await db_client.get(
        f"/api/v1/files/{manager_file_id}", headers=auth_headers(employee)
    )
    assert unlinked_download.status_code == 403
    document = await db_client.post(
        "/api/v1/documents",
        headers=auth_headers(owner),
        json={
            "membership_id": membership_id,
            "document_type": "employment_contract",
            "attachment_file_id": manager_file_id,
            "reminder_days": 30,
        },
    )
    assert document.status_code == 201
    assert document.json()["attachment_file_id"] == manager_file_id
    linked_download = await db_client.get(
        f"/api/v1/files/{manager_file_id}", headers=auth_headers(employee)
    )
    assert linked_download.status_code == 200
    assert linked_download.content == b"protected contract"
    document_id = document.json()["id"]
    detail = await db_client.get(f"/api/v1/documents/{document_id}", headers=auth_headers(employee))
    assert detail.status_code == 200
    metadata_update = await db_client.patch(
        f"/api/v1/documents/{document_id}",
        headers=auth_headers(owner),
        json={
            "version": document.json()["version"],
            "document_type": "employment_contract",
            "document_number": "CONTRACT-2026-001",
            "issued_on": "2026-08-01",
            "expires_on": "2027-08-01",
            "attachment_file_id": manager_file_id,
            "reminder_days": 45,
        },
    )
    assert metadata_update.status_code == 200
    assert metadata_update.json()["review_status"] == "pending_review"
    stale_update = await db_client.patch(
        f"/api/v1/documents/{document_id}",
        headers=auth_headers(owner),
        json={
            "version": document.json()["version"],
            "document_type": "employment_contract",
            "attachment_file_id": manager_file_id,
            "reminder_days": 30,
        },
    )
    assert stale_update.status_code == 409
    employee_upload = await db_client.post(
        "/api/v1/files",
        headers=auth_headers(employee),
        files={"upload": ("signed-contract.pdf", b"signed contract", "application/pdf")},
    )
    assert employee_upload.status_code == 201
    replacement_file_id = employee_upload.json()["id"]
    replacement = await db_client.patch(
        f"/api/v1/documents/{document_id}",
        headers=auth_headers(employee),
        json={
            "version": metadata_update.json()["version"],
            "document_type": "employment_contract",
            "document_number": "CONTRACT-2026-001",
            "issued_on": "2026-08-01",
            "expires_on": "2027-08-01",
            "attachment_file_id": replacement_file_id,
            "reminder_days": 45,
        },
    )
    assert replacement.status_code == 200
    assert replacement.json()["attachment_file_id"] == replacement_file_id
    group = await db_client.post(
        "/api/v1/groups",
        headers=auth_headers(owner),
        json={"code": "REPORT", "name": "Report Team"},
    )
    assert group.status_code == 201
    group_members = await db_client.put(
        f"/api/v1/groups/{group.json()['id']}/members",
        headers=auth_headers(owner),
        json={"membership_ids": [membership_id]},
    )
    assert group_members.status_code == 200
    permission_report_source = await db_client.post(
        "/api/v1/permission-requests",
        headers=auth_headers(employee),
        json={
            "request_type": "one_hour",
            "starts_at": "2026-10-02T09:00:00Z",
            "ends_at": "2026-10-02T10:00:00Z",
            "reason": "Dedicated report coverage",
        },
    )
    assert permission_report_source.status_code == 201
    task_report = await db_client.get(
        "/api/v1/reports/tasks",
        headers=auth_headers(owner),
        params={"group_id": group.json()["id"], "status": "in_progress"},
    )
    assert task_report.status_code == 200
    assert task_report.json()["total"] == 1
    assert task_report.json()["items"][0]["id"] == task_id
    leave_report = await db_client.get(
        "/api/v1/reports/leave",
        headers=auth_headers(owner),
        params={"membership_id": membership_id, "status": "approved"},
    )
    assert leave_report.status_code == 200
    assert leave_report.json()["total"] == 2
    permission_report = await db_client.get(
        "/api/v1/reports/permissions",
        headers=auth_headers(owner),
        params={"group_id": group.json()["id"], "status": "pending"},
    )
    assert permission_report.status_code == 200
    assert permission_report.json()["total"] == 1
    document_report = await db_client.get(
        "/api/v1/reports/documents",
        headers=auth_headers(owner),
        params={"membership_id": membership_id, "status": "pending_review"},
    )
    assert document_report.status_code == 200
    assert document_report.json()["total"] == 1
    ranking_settings = await db_client.put(
        "/api/v1/reports/leaderboard/settings",
        headers=auth_headers(owner),
        json={"visibility": "company", "enabled": True, "anonymize": True},
    )
    assert ranking_settings.status_code == 200
    assert ranking_settings.json()["anonymize"] is True
    ranking_settings_read = await db_client.get(
        "/api/v1/reports/leaderboard/settings", headers=auth_headers(owner)
    )
    assert ranking_settings_read.json() == ranking_settings.json()
    invalid_ranking_period = await db_client.get(
        "/api/v1/reports/leaderboard",
        headers=auth_headers(owner),
        params={"date_from": "2026-10-02", "date_to": "2026-10-01"},
    )
    assert invalid_ranking_period.status_code == 422
    cross_tenant_detail = await db_client.get(
        f"/api/v1/documents/{document_id}", headers=auth_headers(other_owner)
    )
    assert cross_tenant_detail.status_code == 404
    stolen_attachment = await db_client.post(
        "/api/v1/permission-requests",
        headers=auth_headers(employee),
        json={
            "request_type": "one_hour",
            "starts_at": "2026-10-01T09:00:00Z",
            "ends_at": "2026-10-01T10:00:00Z",
            "reason": "Must not steal another uploader file",
            "attachment_file_id": manager_file_id,
        },
    )
    assert stolen_attachment.status_code == 404
    cross_tenant_document = await db_client.post(
        "/api/v1/documents",
        headers=auth_headers(other_owner),
        json={
            "document_type": "employment_contract",
            "attachment_file_id": manager_file_id,
        },
    )
    assert cross_tenant_document.status_code == 404
    deleted = await db_client.delete(
        f"/api/v1/documents/{document_id}?version={replacement.json()['version']}",
        headers=auth_headers(owner),
    )
    assert deleted.status_code == 204
    missing_detail = await db_client.get(
        f"/api/v1/documents/{document_id}", headers=auth_headers(employee)
    )
    assert missing_detail.status_code == 404

    export_headers = {
        **auth_headers(owner),
        "Idempotency-Key": "task-export-001",
    }
    export_payload = {"report_type": "tasks", "export_format": "xlsx", "locale": "en"}
    export = await db_client.post(
        "/api/v1/reports/exports",
        headers=export_headers,
        json=export_payload,
    )
    assert export.status_code == 201
    assert export.json()["status"] == "completed"
    assert export.json()["expires_at"] is not None
    replayed_export = await db_client.post(
        "/api/v1/reports/exports", headers=export_headers, json=export_payload
    )
    assert replayed_export.status_code == 201
    assert replayed_export.json() == export.json()
    download = await db_client.get(
        f"/api/v1/reports/exports/{export.json()['id']}/download",
        headers=auth_headers(owner),
    )
    assert download.status_code == 200
    assert download.content.startswith(b"PK")
    settings = get_settings()
    assert settings.test_database_url is not None
    expiry_engine = create_async_engine(settings.test_database_url)
    async with expiry_engine.begin() as connection:
        await connection.execute(
            update(ExportJob)
            .where(ExportJob.id == UUID(export.json()["id"]))
            .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
    await expiry_engine.dispose()
    cleanup = await db_client.post(
        "/api/v1/reports/exports/cleanup", headers=auth_headers(owner)
    )
    assert cleanup.status_code == 200
    assert cleanup.json()["cleaned"] == 1
    expired_download = await db_client.get(
        f"/api/v1/reports/exports/{export.json()['id']}/download",
        headers=auth_headers(owner),
    )
    assert expired_download.status_code == 410
    assert expired_download.json()["code"] == "export_expired"
