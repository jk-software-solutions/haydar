from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import Permission, require_permission, tenant_context
from app.core.errors import ProblemError
from app.core.subscription_catalog import active_subscription
from app.db.session import get_session
from app.models.platform import (
    CompanySubscription,
    Coupon,
    CouponRedemption,
    SubscriptionPlan,
    SubscriptionRequest,
)

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


class PlanResponse(BaseModel):
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


class SubscriptionResponse(BaseModel):
    id: UUID
    plan: PlanResponse
    billing_cycle: str
    status: str
    starts_at: datetime
    ends_at: datetime
    trial_ends_at: datetime | None
    limits_override: dict[str, object] | None = None
    version: int


class CouponValidateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    plan_id: UUID
    billing_cycle: str = Field(pattern="^(monthly|annual)$")


class CouponValidationResponse(BaseModel):
    valid: bool
    coupon_id: UUID
    discount_type: str
    discount_value: int
    original_amount: int
    discounted_amount: int


class PaymentProviderResponse(BaseModel):
    configured: bool = False
    provider: str | None = None
    detail: str = (
        "No payment provider has been selected. Manual activation is available to platform "
        "administrators."
    )


class SubscriptionRequestCreate(BaseModel):
    plan_id: UUID
    billing_cycle: str = Field(pattern="^(monthly|annual)$")
    coupon_code: str | None = Field(default=None, min_length=2, max_length=64)
    note: str | None = Field(default=None, max_length=1000)


class SubscriptionRequestResponse(BaseModel):
    id: UUID
    plan: PlanResponse
    billing_cycle: str
    status: str
    coupon_code: str | None
    note: str | None
    review_note: str | None
    reviewed_at: datetime | None
    activated_subscription_id: UUID | None
    created_at: datetime


def plan_response(plan: SubscriptionPlan) -> PlanResponse:
    return PlanResponse.model_validate(plan, from_attributes=True)


def subscription_response(
    item: CompanySubscription, plan: SubscriptionPlan
) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=item.id,
        plan=plan_response(plan),
        billing_cycle=item.billing_cycle,
        status=item.status,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        trial_ends_at=item.trial_ends_at,
        limits_override=item.limits_override,
        version=item.version,
    )


def subscription_request_response(
    item: SubscriptionRequest, plan: SubscriptionPlan
) -> SubscriptionRequestResponse:
    return SubscriptionRequestResponse(
        id=item.id,
        plan=plan_response(plan),
        billing_cycle=item.billing_cycle,
        status=item.status,
        coupon_code=item.coupon_code,
        note=item.note,
        review_note=item.review_note,
        reviewed_at=item.reviewed_at,
        activated_subscription_id=item.activated_subscription_id,
        created_at=item.created_at,
    )


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(session: DatabaseSession) -> list[PlanResponse]:
    plans = await session.scalars(
        select(SubscriptionPlan)
        .where(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.monthly_price.asc())
    )
    return [plan_response(plan) for plan in plans]


@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_subscription(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> SubscriptionResponse | None:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SUBSCRIPTION_VIEW)
    row = await active_subscription(session, context.company_id)
    return subscription_response(*row) if row else None


@router.get("/subscription-requests", response_model=list[SubscriptionRequestResponse])
async def list_subscription_requests(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[SubscriptionRequestResponse]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SUBSCRIPTION_VIEW)
    rows = await session.execute(
        select(SubscriptionRequest, SubscriptionPlan)
        .join(SubscriptionPlan, SubscriptionPlan.id == SubscriptionRequest.plan_id)
        .where(SubscriptionRequest.company_id == context.company_id)
        .order_by(SubscriptionRequest.created_at.desc())
        .limit(20)
    )
    return [subscription_request_response(item, plan) for item, plan in rows]


@router.post("/subscription-requests", response_model=SubscriptionRequestResponse, status_code=201)
async def create_subscription_request(
    payload: SubscriptionRequestCreate,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> SubscriptionRequestResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SUBSCRIPTION_MANAGE)
    plan = await session.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == payload.plan_id,
            SubscriptionPlan.is_active.is_(True),
        )
    )
    if plan is None:
        raise ProblemError(
            status=404,
            code="plan_not_found",
            title="Plan not found",
            detail="The selected subscription plan is not available.",
        )
    pending = await session.scalar(
        select(SubscriptionRequest.id).where(
            SubscriptionRequest.company_id == context.company_id,
            SubscriptionRequest.status == "pending",
        )
    )
    if pending is not None:
        raise ProblemError(
            status=409,
            code="subscription_request_pending",
            title="Subscription request already pending",
            detail="A subscription request is already awaiting platform approval.",
        )
    item = SubscriptionRequest(
        company_id=context.company_id,
        requested_by_membership_id=context.membership.id,
        plan_id=plan.id,
        billing_cycle=payload.billing_cycle,
        coupon_code=payload.coupon_code.strip().upper() if payload.coupon_code else None,
        note=payload.note.strip() if payload.note else None,
    )
    session.add(item)
    await session.flush()
    await session.commit()
    await session.refresh(item)
    return subscription_request_response(item, plan)


@router.post("/coupons/validate", response_model=CouponValidationResponse)
async def validate_coupon(
    payload: CouponValidateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> CouponValidationResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.SUBSCRIPTION_MANAGE)
    now = datetime.now(UTC)
    coupon = await session.scalar(
        select(Coupon).where(
            Coupon.code == payload.code.strip().upper(),
            Coupon.is_active.is_(True),
            Coupon.valid_from <= now,
            Coupon.valid_until > now,
        )
    )
    plan = await session.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.id == payload.plan_id, SubscriptionPlan.is_active.is_(True)
        )
    )
    redeemed = None
    if coupon:
        redeemed = await session.scalar(
            select(CouponRedemption.id).where(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.company_id == context.company_id,
            )
        )
    if (
        coupon is None
        or plan is None
        or redeemed is not None
        or (coupon.max_redemptions is not None and coupon.redeemed_count >= coupon.max_redemptions)
        or (coupon.plan_id is not None and coupon.plan_id != payload.plan_id)
        or (coupon.billing_cycle is not None and coupon.billing_cycle != payload.billing_cycle)
    ):
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="coupon_invalid",
            title="Coupon is invalid",
            detail="The coupon is expired, unavailable, or was already used by this company.",
        )
    original = plan.monthly_price if payload.billing_cycle == "monthly" else plan.annual_price
    discount = (
        original * coupon.discount_value // 100
        if coupon.discount_type == "percent"
        else coupon.discount_value
    )
    return CouponValidationResponse(
        valid=True,
        coupon_id=coupon.id,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        original_amount=original,
        discounted_amount=max(0, original - discount),
    )


@router.get("/payment-provider", response_model=PaymentProviderResponse)
async def payment_provider_status() -> PaymentProviderResponse:
    return PaymentProviderResponse()
