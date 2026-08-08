from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.config import get_settings


def auth_headers(session: dict[str, Any], idempotency_key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
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


async def test_platform_plan_coupon_support_and_suspension_lifecycle(
    db_client: httpx.AsyncClient,
) -> None:
    admin_email = "platform-admin@example.com"
    admin = await register_company(db_client, "Platform Admin", admin_email)
    target = await register_company(db_client, "Platform Customer", "customer@example.com")
    settings = get_settings()
    original_admins = settings.platform_admin_emails
    settings.platform_admin_emails = admin_email
    try:
        admin_headers = auth_headers(admin)
        created_plan = await db_client.post(
            "/api/v1/platform/plans",
            headers=admin_headers,
            json={
                "code": "growth_test",
                "name": "Growth Test",
                "description": "Lifecycle coverage",
                "monthly_price": 25000,
                "annual_price": 250000,
                "currency": "sar",
                "limits": {"employees": 100, "branches": 10, "storage_mb": 5000},
                "features": {"reports": "advanced", "documents": True},
                "support_level": "priority",
                "is_active": True,
            },
        )
        assert created_plan.status_code == 201
        plan = created_plan.json()
        assert plan["code"] == "GROWTH_TEST"
        assert plan["currency"] == "SAR"

        updated_plan = await db_client.patch(
            f"/api/v1/platform/plans/{plan['id']}",
            headers=admin_headers,
            json={"version": plan["version"], "monthly_price": 24000},
        )
        assert updated_plan.status_code == 200
        assert updated_plan.json()["version"] == 2
        stale_plan = await db_client.patch(
            f"/api/v1/platform/plans/{plan['id']}",
            headers=admin_headers,
            json={"version": plan["version"], "name": "Stale write"},
        )
        assert stale_plan.status_code == 409
        assert stale_plan.json()["code"] == "concurrency_conflict"

        now = datetime.now(UTC)
        coupon_response = await db_client.post(
            "/api/v1/platform/coupons",
            headers=admin_headers,
            json={
                "code": "growth20",
                "discount_type": "percent",
                "discount_value": 20,
                "plan_id": plan["id"],
                "billing_cycle": "monthly",
                "max_redemptions": 1,
                "valid_from": (now - timedelta(minutes=1)).isoformat(),
                "valid_until": (now + timedelta(days=10)).isoformat(),
            },
        )
        assert coupon_response.status_code == 201

        activation = {
            "company_status": "active",
            "plan_id": plan["id"],
            "billing_cycle": "monthly",
            "duration_days": 30,
            "coupon_code": "GROWTH20",
            "activation_note": "Activate customer with approved offer",
        }
        mutation_headers = auth_headers(admin, "platform-activation-0001")
        activated = await db_client.patch(
            f"/api/v1/platform/companies/{target['session']['company']['id']}",
            headers=mutation_headers,
            json=activation,
        )
        assert activated.status_code == 200
        replayed = await db_client.patch(
            f"/api/v1/platform/companies/{target['session']['company']['id']}",
            headers=mutation_headers,
            json=activation,
        )
        assert replayed.status_code == 200
        assert replayed.json() == activated.json()
        coupons = await db_client.get("/api/v1/platform/coupons", headers=admin_headers)
        assert coupons.status_code == 200
        redeemed = next(item for item in coupons.json() if item["code"] == "GROWTH20")
        assert redeemed["redeemed_count"] == 1

        support = await db_client.post(
            "/api/v1/platform/support-mode",
            headers=admin_headers,
            json={
                "company_id": target["session"]["company"]["id"],
                "reason": "Investigate customer configuration",
                "duration_minutes": 30,
            },
        )
        assert support.status_code == 201
        active_support = await db_client.get("/api/v1/platform/support-mode", headers=admin_headers)
        assert active_support.status_code == 200
        assert [item["id"] for item in active_support.json()] == [support.json()["id"]]
        ended = await db_client.post(
            f"/api/v1/platform/support-mode/{support.json()['id']}/end",
            headers=admin_headers,
        )
        assert ended.status_code == 200
        assert ended.json()["ended_at"] is not None

        suspended = await db_client.patch(
            f"/api/v1/platform/companies/{target['session']['company']['id']}",
            headers=auth_headers(admin, "platform-suspension-0001"),
            json={
                "company_status": "suspended",
                "activation_note": "Suspend customer after account review",
            },
        )
        assert suspended.status_code == 200
        refresh = await db_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": target["refresh_token"]},
        )
        assert refresh.status_code == 401
    finally:
        settings.platform_admin_emails = original_admins
