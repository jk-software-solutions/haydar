from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import Company
from app.models.platform import CompanySubscription, SubscriptionPlan

BUILTIN_PLANS: tuple[dict[str, object], ...] = (
    {
        "id": UUID("10000000-0000-0000-0000-000000000001"),
        "code": "FREE_TRIAL",
        "name": "Free Trial",
        "description": "Evaluation plan",
        "monthly_price": 0,
        "annual_price": 0,
        "limits": {"employees": 10, "branches": 3, "storage_mb": 100},
        "features": {
            "gps": True,
            "qr": False,
            "tasks": True,
            "documents": False,
            "reports": "basic",
        },
        "support_level": "community",
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000002"),
        "code": "BASIC",
        "name": "Basic",
        "description": "Small teams",
        "monthly_price": 19_900,
        "annual_price": 199_000,
        "limits": {"employees": 50, "branches": 3, "storage_mb": 2048},
        "features": {"gps": True, "qr": True, "tasks": True, "documents": True, "reports": "basic"},
        "support_level": "standard",
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000003"),
        "code": "PROFESSIONAL",
        "name": "Professional",
        "description": "Growing organizations",
        "monthly_price": 49_900,
        "annual_price": 499_000,
        "limits": {"employees": 250, "branches": 20, "storage_mb": 10_240},
        "features": {
            "gps": True,
            "qr": True,
            "tasks": True,
            "documents": True,
            "reports": "advanced",
        },
        "support_level": "priority",
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000004"),
        "code": "ENTERPRISE",
        "name": "Enterprise",
        "description": "Custom enterprise plan",
        "monthly_price": 0,
        "annual_price": 0,
        "limits": {"employees": 1_000_000, "branches": 1_000_000, "storage_mb": 1_000_000},
        "features": {
            "gps": True,
            "qr": True,
            "tasks": True,
            "documents": True,
            "reports": "advanced",
        },
        "support_level": "dedicated",
    },
)


async def seed_builtin_plans(session: AsyncSession) -> None:
    existing = set(await session.scalars(select(SubscriptionPlan.code)))
    session.add_all(
        [
            SubscriptionPlan(currency="SAR", **plan)
            for plan in BUILTIN_PLANS
            if plan["code"] not in existing
        ]
    )
    await session.flush()


async def create_trial_subscription(session: AsyncSession, company: Company) -> None:
    plan = await session.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.code == "FREE_TRIAL")
    )
    if plan is None:
        return
    now = datetime.now(UTC)
    trial_end = now + timedelta(days=14)
    session.add(
        CompanySubscription(
            company_id=company.id,
            plan_id=plan.id,
            billing_cycle="trial",
            status="trial",
            starts_at=now,
            ends_at=trial_end,
            trial_ends_at=trial_end,
            activation_note="Automatic company registration trial",
        )
    )


async def active_subscription(
    session: AsyncSession, company_id: UUID
) -> tuple[CompanySubscription, SubscriptionPlan] | None:
    now = datetime.now(UTC)
    row = (
        await session.execute(
            select(CompanySubscription, SubscriptionPlan)
            .join(SubscriptionPlan, SubscriptionPlan.id == CompanySubscription.plan_id)
            .where(
                CompanySubscription.company_id == company_id,
                CompanySubscription.status.in_(("active", "trial")),
                CompanySubscription.starts_at <= now,
                CompanySubscription.ends_at > now,
            )
            .order_by(CompanySubscription.ends_at.desc())
            .limit(1)
        )
    ).first()
    return (row[0], row[1]) if row else None


def plan_limit(plan: SubscriptionPlan, name: str) -> int:
    value = plan.limits.get(name, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        return int(value)
    return 0
