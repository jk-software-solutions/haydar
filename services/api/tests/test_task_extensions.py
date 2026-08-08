from datetime import UTC, datetime, timedelta
from typing import Any

import httpx


def auth_headers(session: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def register_company(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register-company",
        json={
            "company_name": "Task Extension Company",
            "owner_full_name": "Task Owner",
            "owner_email": "task-extension-owner@example.com",
            "password": "ChangeMe123!",
        },
    )
    assert response.status_code == 201
    return response.json()


async def invite_employee(client: httpx.AsyncClient, owner: dict[str, Any]) -> dict[str, Any]:
    invitation = await client.post(
        "/api/v1/invitations",
        headers=auth_headers(owner),
        json={
            "email": "task-extension-worker@example.com",
            "full_name": "Task Worker",
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


async def test_task_extension_request_requires_explicit_manager_decision(
    db_client: httpx.AsyncClient,
) -> None:
    owner = await register_company(db_client)
    employee = await invite_employee(db_client, owner)
    due_at = datetime.now(UTC) + timedelta(days=1)
    task_response = await db_client.post(
        "/api/v1/tasks",
        headers=auth_headers(owner),
        json={
            "title": "Finish field audit",
            "description": "Complete and upload the field audit evidence.",
            "priority": "high",
            "due_at": due_at.isoformat(),
            "membership_ids": [employee["session"]["membership_id"]],
        },
    )
    assert task_response.status_code == 201
    task = task_response.json()
    requested_due_at = due_at + timedelta(days=2)
    requested = await db_client.post(
        f"/api/v1/tasks/{task['id']}/status",
        headers=auth_headers(employee),
        json={
            "version": task["version"],
            "status": "needs_more_time",
            "reason": "Awaiting a required site access approval",
            "requested_due_at": requested_due_at.isoformat(),
        },
    )
    assert requested.status_code == 200
    requested_task = requested.json()
    assert requested_task["latest_extension"]["status"] == "pending"
    assert requested_task["latest_extension"]["reason"].startswith("Awaiting")

    repeated = await db_client.post(
        f"/api/v1/tasks/{task['id']}/status",
        headers=auth_headers(employee),
        json={
            "version": requested_task["version"],
            "status": "needs_more_time",
            "reason": "A second extension should not be opened",
            "requested_due_at": (requested_due_at + timedelta(days=1)).isoformat(),
        },
    )
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "task_extension_pending"

    approved_due_at = requested_due_at + timedelta(hours=4)
    approved = await db_client.post(
        f"/api/v1/tasks/{task['id']}/extension-decision",
        headers=auth_headers(owner),
        json={
            "version": requested_task["version"],
            "decision": "approved",
            "new_due_at": approved_due_at.isoformat(),
            "comment": "Approved after confirming site access timing",
        },
    )
    assert approved.status_code == 200
    approved_task = approved.json()
    assert approved_task["status"] == "in_progress"
    assert approved_task["latest_extension"]["status"] == "approved"
    assert approved_task["latest_extension"]["decision_comment"].startswith("Approved")
    assert datetime.fromisoformat(approved_task["due_at"]) == approved_due_at

    second_decision = await db_client.post(
        f"/api/v1/tasks/{task['id']}/extension-decision",
        headers=auth_headers(owner),
        json={
            "version": approved_task["version"],
            "decision": "rejected",
            "comment": "Cannot decide the same request twice",
        },
    )
    assert second_decision.status_code == 409
    assert second_decision.json()["code"] == "task_extension_not_pending"
