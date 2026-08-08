from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.config import get_settings
from app.core.errors import ProblemError
from app.db.session import get_session
from app.models.identity import Company, CompanyMembership, User
from app.models.organization import Branch
from app.models.platform import (
    CompanySubscription,
    Coupon,
    PlatformAuditLog,
    PlatformSetting,
    SubscriptionPlan,
    SupportSession,
)

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


class PlatformDashboardResponse(BaseModel):
    companies: int
    active_companies: int
    trial_companies: int
    suspended_companies: int
    active_subscriptions: int
    expired_subscriptions: int
    employees: int
    branches: int


class PlatformCompanyResponse(BaseModel):
    id: UUID
    display_name: str
    technical_name: str
    status: str
    default_locale: str
    timezone: str
    employees: int
    branches: int
    plan_code: str | None
    subscription_status: str | None
    subscription_ends_at: datetime | None
    created_at: datetime


class CompanyAdminUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_status: Literal["active", "trial", "suspended", "inactive"] | None = None
    plan_id: UUID | None = None
    billing_cycle: Literal["trial", "monthly", "annual"] | None = None
    duration_days: int | None = Field(default=None, ge=1, le=3660)
    activation_note: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def validate_subscription_fields(self) -> "CompanyAdminUpdateRequest":
        values = (self.plan_id, self.billing_cycle, self.duration_days)
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("plan_id, billing_cycle, and duration_days must be supplied together")
        return self


class CouponCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: Literal["percent", "fixed"]
    discount_value: int = Field(ge=1)
    max_redemptions: int | None = Field(default=None, ge=1)
    valid_from: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def validate_coupon(self) -> "CouponCreateRequest":
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValueError("percentage discount cannot exceed 100")
        return self


class CouponResponse(BaseModel):
    id: UUID
    code: str
    discount_type: str
    discount_value: int
    max_redemptions: int | None
    redeemed_count: int
    valid_from: datetime
    valid_until: datetime
    is_active: bool


class SupportModeRequest(BaseModel):
    company_id: UUID
    reason: str = Field(min_length=5, max_length=2000)
    duration_minutes: int = Field(default=30, ge=5, le=120)


class SupportModeResponse(BaseModel):
    id: UUID
    company_id: UUID
    company_name: str
    reason: str
    expires_at: datetime
    banner: str


class PlatformSettingRequest(BaseModel):
    value: dict[str, object]


async def require_platform_admin(auth_session: CurrentAuthSession) -> User:
    user, _company, _membership = auth_session
    if user.email.lower() not in get_settings().platform_admin_email_set:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="platform_admin_required",
            title="Platform administrator required",
            detail="This endpoint is restricted to explicitly configured platform administrators.",
        )
    return user


async def company_response(session: AsyncSession, company: Company) -> PlatformCompanyResponse:
    employee_count = int(
        await session.scalar(
            select(func.count())
            .select_from(CompanyMembership)
            .where(
                CompanyMembership.company_id == company.id,
                CompanyMembership.status == "active",
            )
        )
        or 0
    )
    branch_count = int(
        await session.scalar(
            select(func.count()).select_from(Branch).where(Branch.company_id == company.id)
        )
        or 0
    )
    subscription_row = (
        await session.execute(
            select(CompanySubscription, SubscriptionPlan)
            .join(SubscriptionPlan, SubscriptionPlan.id == CompanySubscription.plan_id)
            .where(CompanySubscription.company_id == company.id)
            .order_by(CompanySubscription.created_at.desc())
            .limit(1)
        )
    ).first()
    subscription = subscription_row[0] if subscription_row else None
    plan = subscription_row[1] if subscription_row else None
    return PlatformCompanyResponse(
        id=company.id,
        display_name=company.display_name,
        technical_name=company.technical_name,
        status=company.status,
        default_locale=company.default_locale,
        timezone=company.timezone,
        employees=employee_count,
        branches=branch_count,
        plan_code=plan.code if plan else None,
        subscription_status=subscription.status if subscription else None,
        subscription_ends_at=subscription.ends_at if subscription else None,
        created_at=company.created_at,
    )


@router.get("/dashboard", response_model=PlatformDashboardResponse)
async def platform_dashboard(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> PlatformDashboardResponse:
    await require_platform_admin(auth_session)
    now = datetime.now(UTC)

    async def company_count(company_status: str | None = None) -> int:
        statement = select(func.count()).select_from(Company)
        if company_status:
            statement = statement.where(Company.status == company_status)
        return int(await session.scalar(statement) or 0)

    return PlatformDashboardResponse(
        companies=await company_count(),
        active_companies=await company_count("active"),
        trial_companies=await company_count("trial"),
        suspended_companies=await company_count("suspended"),
        active_subscriptions=int(
            await session.scalar(
                select(func.count())
                .select_from(CompanySubscription)
                .where(
                    CompanySubscription.status.in_(("active", "trial")),
                    CompanySubscription.ends_at > now,
                )
            )
            or 0
        ),
        expired_subscriptions=int(
            await session.scalar(
                select(func.count())
                .select_from(CompanySubscription)
                .where(CompanySubscription.ends_at <= now)
            )
            or 0
        ),
        employees=int(
            await session.scalar(select(func.count()).select_from(CompanyMembership)) or 0
        ),
        branches=int(await session.scalar(select(func.count()).select_from(Branch)) or 0),
    )


@router.get("/companies", response_model=list[PlatformCompanyResponse])
async def list_platform_companies(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[PlatformCompanyResponse]:
    await require_platform_admin(auth_session)
    companies = list(
        await session.scalars(select(Company).order_by(Company.created_at.desc()).limit(2000))
    )
    return [await company_response(session, company) for company in companies]


@router.patch("/companies/{company_id}", response_model=PlatformCompanyResponse)
async def update_platform_company(
    company_id: UUID,
    payload: CompanyAdminUpdateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> PlatformCompanyResponse:
    admin = await require_platform_admin(auth_session)
    company = await session.scalar(
        select(Company).where(Company.id == company_id).with_for_update()
    )
    if company is None:
        raise ProblemError(
            status=404,
            code="company_not_found",
            title="Company not found",
            detail="The company does not exist.",
        )
    changes: dict[str, object] = {"note": payload.activation_note}
    if payload.company_status:
        changes["old_status"] = company.status
        company.status = payload.company_status
        changes["new_status"] = company.status
    if payload.plan_id and payload.billing_cycle and payload.duration_days:
        plan = await session.scalar(
            select(SubscriptionPlan).where(
                SubscriptionPlan.id == payload.plan_id, SubscriptionPlan.is_active.is_(True)
            )
        )
        if plan is None:
            raise ProblemError(
                status=404,
                code="plan_not_found",
                title="Plan not found",
                detail="The active subscription plan does not exist.",
            )
        active_items = await session.scalars(
            select(CompanySubscription)
            .where(
                CompanySubscription.company_id == company.id,
                CompanySubscription.status.in_(("active", "trial")),
            )
            .with_for_update()
        )
        for item in active_items:
            item.status = "replaced"
            item.version += 1
        now = datetime.now(UTC)
        subscription = CompanySubscription(
            company_id=company.id,
            plan_id=plan.id,
            billing_cycle=payload.billing_cycle,
            status="trial" if payload.billing_cycle == "trial" else "active",
            starts_at=now,
            ends_at=now + timedelta(days=payload.duration_days),
            trial_ends_at=now + timedelta(days=payload.duration_days)
            if payload.billing_cycle == "trial"
            else None,
            activation_note=payload.activation_note,
        )
        session.add(subscription)
        company.status = "trial" if payload.billing_cycle == "trial" else "active"
        changes.update(
            {
                "plan": plan.code,
                "billing_cycle": payload.billing_cycle,
                "duration_days": payload.duration_days,
            }
        )
    session.add(
        PlatformAuditLog(
            platform_user_id=admin.id,
            action="company.updated",
            target_type="company",
            target_id=company.id,
            details=changes,
        )
    )
    await session.commit()
    await session.refresh(company)
    return await company_response(session, company)


@router.post("/coupons", response_model=CouponResponse, status_code=201)
async def create_coupon(
    payload: CouponCreateRequest, auth_session: CurrentAuthSession, session: DatabaseSession
) -> CouponResponse:
    admin = await require_platform_admin(auth_session)
    code = payload.code.strip().upper()
    if await session.scalar(select(Coupon.id).where(Coupon.code == code)):
        raise ProblemError(
            status=409,
            code="coupon_exists",
            title="Coupon already exists",
            detail="Use a unique coupon code.",
        )
    item = Coupon(code=code, **payload.model_dump(exclude={"code"}))
    session.add(item)
    await session.flush()
    session.add(
        PlatformAuditLog(
            platform_user_id=admin.id,
            action="coupon.created",
            target_type="coupon",
            target_id=item.id,
            details={"code": code},
        )
    )
    await session.commit()
    await session.refresh(item)
    return CouponResponse.model_validate(item, from_attributes=True)


@router.get("/coupons", response_model=list[CouponResponse])
async def list_coupons(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[CouponResponse]:
    await require_platform_admin(auth_session)
    items = await session.scalars(select(Coupon).order_by(Coupon.created_at.desc()))
    return [CouponResponse.model_validate(item, from_attributes=True) for item in items]


@router.post("/support-mode", response_model=SupportModeResponse, status_code=201)
async def start_support_mode(
    payload: SupportModeRequest, auth_session: CurrentAuthSession, session: DatabaseSession
) -> SupportModeResponse:
    admin = await require_platform_admin(auth_session)
    company = await session.scalar(select(Company).where(Company.id == payload.company_id))
    if company is None:
        raise ProblemError(
            status=404,
            code="company_not_found",
            title="Company not found",
            detail="The company does not exist.",
        )
    expires_at = datetime.now(UTC) + timedelta(minutes=payload.duration_minutes)
    item = SupportSession(
        company_id=company.id,
        platform_user_id=admin.id,
        reason=payload.reason,
        expires_at=expires_at,
    )
    session.add(item)
    await session.flush()
    session.add(
        PlatformAuditLog(
            platform_user_id=admin.id,
            action="support.started",
            target_type="company",
            target_id=company.id,
            details={"reason": payload.reason, "expires_at": expires_at.isoformat()},
        )
    )
    await session.commit()
    return SupportModeResponse(
        id=item.id,
        company_id=company.id,
        company_name=company.display_name,
        reason=item.reason,
        expires_at=item.expires_at,
        banner=f"SUPPORT MODE — {company.display_name}",
    )


@router.put("/settings/{key}")
async def update_platform_setting(
    key: str,
    payload: PlatformSettingRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> dict[str, object]:
    admin = await require_platform_admin(auth_session)
    if len(key) > 120:
        raise ProblemError(
            status=422,
            code="setting_key_invalid",
            title="Invalid setting key",
            detail="The setting key is too long.",
        )
    item = await session.get(PlatformSetting, key)
    if item is None:
        item = PlatformSetting(key=key, value=payload.value, updated_by_user_id=admin.id)
        session.add(item)
    else:
        item.value = payload.value
        item.updated_by_user_id = admin.id
    await session.commit()
    return {"key": key, "value": payload.value}
