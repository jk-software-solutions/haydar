from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import tenant_context
from app.core.config import get_settings
from app.core.errors import ProblemError
from app.db.session import get_session
from app.models.identity import Company, CompanyMembership, RefreshSession, User
from app.models.organization import Branch
from app.models.platform import (
    CompanySubscription,
    Coupon,
    CouponRedemption,
    PlatformAuditLog,
    PlatformSetting,
    SubscriptionPlan,
    SupportSession,
)
from app.services.idempotency import IdempotencyKey, begin_idempotency, complete_idempotency

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
    subscription_id: UUID | None
    subscription_version: int | None
    created_at: datetime


class CompanyAdminUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_status: Literal["active", "trial", "suspended", "inactive"] | None = None
    plan_id: UUID | None = None
    billing_cycle: Literal["trial", "monthly", "annual"] | None = None
    duration_days: int | None = Field(default=None, ge=1, le=3660)
    coupon_code: str | None = Field(default=None, min_length=2, max_length=64)
    activation_note: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def validate_subscription_fields(self) -> "CompanyAdminUpdateRequest":
        values = (self.plan_id, self.billing_cycle, self.duration_days)
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("plan_id, billing_cycle, and duration_days must be supplied together")
        if self.coupon_code is not None and self.plan_id is None:
            raise ValueError("coupon_code can only be used with a subscription activation")
        if self.coupon_code is not None and self.billing_cycle == "trial":
            raise ValueError("coupons cannot be applied to trial subscriptions")
        return self


class PlanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=4000)
    monthly_price: int = Field(ge=0)
    annual_price: int = Field(ge=0)
    currency: str = Field(default="SAR", min_length=3, max_length=3)
    limits: dict[str, object] = Field(default_factory=dict)
    features: dict[str, object] = Field(default_factory=dict)
    support_level: str = Field(default="standard", min_length=2, max_length=40)
    is_active: bool = True


class PlanUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    monthly_price: int | None = Field(default=None, ge=0)
    annual_price: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    limits: dict[str, object] | None = None
    features: dict[str, object] | None = None
    support_level: str | None = Field(default=None, min_length=2, max_length=40)
    is_active: bool | None = None


class PlanAdminResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str
    monthly_price: int
    annual_price: int
    currency: str
    limits: dict[str, object]
    features: dict[str, object]
    support_level: str
    is_active: bool
    version: int


class CouponCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: Literal["percent", "fixed"]
    discount_value: int = Field(ge=1)
    plan_id: UUID | None = None
    billing_cycle: Literal["monthly", "annual"] | None = None
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
    plan_id: UUID | None
    billing_cycle: str | None
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
    started_at: datetime
    expires_at: datetime
    ended_at: datetime | None
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
        subscription_id=subscription.id if subscription else None,
        subscription_version=subscription.version if subscription else None,
        created_at=company.created_at,
    )


def support_response(item: SupportSession, company: Company) -> SupportModeResponse:
    return SupportModeResponse(
        id=item.id,
        company_id=company.id,
        company_name=company.display_name,
        reason=item.reason,
        started_at=item.started_at,
        expires_at=item.expires_at,
        ended_at=item.ended_at,
        banner=f"SUPPORT MODE — {company.display_name}",
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


@router.get("/plans", response_model=list[PlanAdminResponse])
async def list_admin_plans(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[PlanAdminResponse]:
    await require_platform_admin(auth_session)
    items = await session.scalars(
        select(SubscriptionPlan).order_by(SubscriptionPlan.monthly_price, SubscriptionPlan.code)
    )
    return [PlanAdminResponse.model_validate(item, from_attributes=True) for item in items]


@router.post("/plans", response_model=PlanAdminResponse, status_code=201)
async def create_plan(
    payload: PlanCreateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> PlanAdminResponse:
    admin = await require_platform_admin(auth_session)
    code = payload.code.strip().upper()
    if await session.scalar(select(SubscriptionPlan.id).where(SubscriptionPlan.code == code)):
        raise ProblemError(
            status=409,
            code="plan_exists",
            title="Plan already exists",
            detail="Use a unique plan code.",
        )
    item = SubscriptionPlan(
        **payload.model_dump(exclude={"code", "currency"}),
        code=code,
        currency=payload.currency.upper(),
    )
    session.add(item)
    await session.flush()
    session.add(
        PlatformAuditLog(
            platform_user_id=admin.id,
            action="plan.created",
            target_type="subscription_plan",
            target_id=item.id,
            details={"code": code},
        )
    )
    await session.commit()
    return PlanAdminResponse.model_validate(item, from_attributes=True)


@router.patch("/plans/{plan_id}", response_model=PlanAdminResponse)
async def update_plan(
    plan_id: UUID,
    payload: PlanUpdateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> PlanAdminResponse:
    admin = await require_platform_admin(auth_session)
    item = await session.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id).with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="plan_not_found",
            title="Plan not found",
            detail="The subscription plan does not exist.",
        )
    if item.version != payload.version:
        raise ProblemError(
            status=409,
            code="concurrency_conflict",
            title="Plan changed",
            detail="Reload the plan before updating it.",
        )
    changes = payload.model_dump(exclude={"version"}, exclude_unset=True)
    if changes.get("currency"):
        changes["currency"] = str(changes["currency"]).upper()
    for field, value in changes.items():
        setattr(item, field, value)
    item.version += 1
    session.add(
        PlatformAuditLog(
            platform_user_id=admin.id,
            action="plan.updated",
            target_type="subscription_plan",
            target_id=item.id,
            details={"version": item.version, "fields": sorted(changes)},
        )
    )
    await session.commit()
    return PlanAdminResponse.model_validate(item, from_attributes=True)


@router.patch("/companies/{company_id}", response_model=PlatformCompanyResponse)
async def update_platform_company(
    company_id: UUID,
    payload: CompanyAdminUpdateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey = None,
) -> PlatformCompanyResponse:
    admin = await require_platform_admin(auth_session)
    context = tenant_context(auth_session)
    idempotency, replay = await begin_idempotency(
        session,
        context,
        f"platform.company.update:{company_id}",
        idempotency_key,
        payload,
    )
    if replay is not None:
        return PlatformCompanyResponse.model_validate(replay)
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
        if payload.company_status in {"suspended", "inactive"}:
            revoked_at = datetime.now(UTC)
            await session.execute(
                sql_update(RefreshSession)
                .where(
                    RefreshSession.company_id == company.id,
                    RefreshSession.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            changes["sessions_revoked"] = True
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
        await session.flush()
        if payload.coupon_code:
            coupon = await session.scalar(
                select(Coupon)
                .where(Coupon.code == payload.coupon_code.strip().upper())
                .with_for_update()
            )
            now = datetime.now(UTC)
            previous_redemption = None
            if coupon is not None:
                previous_redemption = await session.scalar(
                    select(CouponRedemption.id).where(
                        CouponRedemption.coupon_id == coupon.id,
                        CouponRedemption.company_id == company.id,
                    )
                )
            if (
                coupon is None
                or not coupon.is_active
                or coupon.valid_from > now
                or coupon.valid_until <= now
                or previous_redemption is not None
                or (
                    coupon.max_redemptions is not None
                    and coupon.redeemed_count >= coupon.max_redemptions
                )
                or (coupon.plan_id is not None and coupon.plan_id != plan.id)
                or (
                    coupon.billing_cycle is not None
                    and coupon.billing_cycle != payload.billing_cycle
                )
            ):
                raise ProblemError(
                    status=409,
                    code="coupon_invalid",
                    title="Coupon is invalid",
                    detail="The coupon cannot be redeemed for this subscription activation.",
                )
            coupon.redeemed_count += 1
            session.add(
                CouponRedemption(
                    coupon_id=coupon.id,
                    company_id=company.id,
                    subscription_id=subscription.id,
                )
            )
            changes["coupon"] = coupon.code
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
    await session.flush()
    result = await company_response(session, company)
    complete_idempotency(idempotency, result, status.HTTP_200_OK)
    await session.commit()
    return result


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
    if payload.plan_id is not None and not await session.get(SubscriptionPlan, payload.plan_id):
        raise ProblemError(
            status=404,
            code="plan_not_found",
            title="Plan not found",
            detail="The coupon restriction references a plan that does not exist.",
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
    return support_response(item, company)


@router.get("/support-mode", response_model=list[SupportModeResponse])
async def list_active_support_modes(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[SupportModeResponse]:
    admin = await require_platform_admin(auth_session)
    now = datetime.now(UTC)
    rows = (
        await session.execute(
            select(SupportSession, Company)
            .join(Company, Company.id == SupportSession.company_id)
            .where(
                SupportSession.platform_user_id == admin.id,
                SupportSession.ended_at.is_(None),
                SupportSession.expires_at > now,
            )
            .order_by(SupportSession.started_at.desc())
        )
    ).all()
    return [support_response(item, company) for item, company in rows]


@router.post("/support-mode/{support_session_id}/end", response_model=SupportModeResponse)
async def end_support_mode(
    support_session_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> SupportModeResponse:
    admin = await require_platform_admin(auth_session)
    row = (
        await session.execute(
            select(SupportSession, Company)
            .join(Company, Company.id == SupportSession.company_id)
            .where(
                SupportSession.id == support_session_id,
                SupportSession.platform_user_id == admin.id,
            )
            .with_for_update()
        )
    ).first()
    if row is None:
        raise ProblemError(
            status=404,
            code="support_session_not_found",
            title="Support session not found",
            detail="The support session does not exist or belongs to another administrator.",
        )
    item, company = row
    if item.ended_at is None:
        item.ended_at = datetime.now(UTC)
        session.add(
            PlatformAuditLog(
                platform_user_id=admin.id,
                action="support.ended",
                target_type="company",
                target_id=company.id,
                details={"support_session_id": str(item.id)},
            )
        )
        await session.commit()
    return support_response(item, company)


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
