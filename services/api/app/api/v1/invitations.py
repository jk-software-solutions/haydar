from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import AuthTokenResponse, CurrentAuthSession, issue_tokens
from app.core.authorization import Permission, RoleCode, require_permission, tenant_context
from app.core.errors import ProblemError
from app.core.security import hash_password
from app.core.subscription_catalog import active_subscription, plan_limit
from app.db.session import get_session
from app.models.identity import Company, CompanyMembership, Invitation, MembershipRole, User
from app.models.organization import EmployeeProfile

router = APIRouter()
activation_router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]
INVITABLE_ROLES = {
    RoleCode.MANAGER,
    RoleCode.SUPERVISOR,
    RoleCode.HR_OFFICER,
    RoleCode.EMPLOYEE,
}


class CreateInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=2, max_length=160)
    role_code: RoleCode

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role_code: RoleCode
    status: str
    expires_at: datetime


class CreatedInvitationResponse(InvitationResponse):
    activation_token: str


class InvitationListResponse(BaseModel):
    items: list[InvitationResponse]
    page: int
    page_size: int
    total: int


class ActivateInvitationRequest(BaseModel):
    activation_token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=8, max_length=128)


def invitation_response(invitation: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        full_name=invitation.full_name,
        role_code=RoleCode(invitation.role_code),
        status=invitation.status,
        expires_at=invitation.expires_at,
    )


@router.post("", response_model=CreatedInvitationResponse, status_code=201)
async def create_invitation(
    payload: CreateInvitationRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> CreatedInvitationResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.MEMBERS_CREATE)
    subscription = await active_subscription(session, context.company_id)
    employee_limit = (
        plan_limit(subscription[1], "employees", subscription[0].limits_override)
        if subscription
        else 0
    )
    active_count = int(
        await session.scalar(
            select(func.count())
            .select_from(CompanyMembership)
            .where(
                CompanyMembership.company_id == context.company_id,
                CompanyMembership.status == "active",
            )
        )
        or 0
    )
    pending_count = int(
        await session.scalar(
            select(func.count())
            .select_from(Invitation)
            .where(
                Invitation.company_id == context.company_id,
                Invitation.status == "pending",
            )
        )
        or 0
    )
    if subscription is None or active_count + pending_count >= employee_limit:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="subscription_employee_limit",
            title="Employee limit reached",
            detail="Upgrade or extend the subscription before inviting another employee.",
        )
    if payload.role_code not in INVITABLE_ROLES:
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="role_not_invitable",
            title="Role cannot be invited",
            detail="Company owner memberships cannot be created by invitation.",
        )
    existing_membership = await session.scalar(
        select(CompanyMembership.id)
        .join(User, User.id == CompanyMembership.user_id)
        .where(
            CompanyMembership.company_id == context.company_id,
            User.email == payload.email,
        )
    )
    if existing_membership is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="membership_already_exists",
            title="Membership already exists",
            detail="This email already belongs to the company.",
        )

    raw_token = token_urlsafe(48)
    invitation = Invitation(
        company_id=context.company_id,
        invited_by_membership_id=context.membership.id,
        email=payload.email,
        full_name=payload.full_name.strip(),
        role_code=payload.role_code.value,
        token_hash=sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)
    return CreatedInvitationResponse(
        **invitation_response(invitation).model_dump(),
        activation_token=raw_token,
    )


@router.get("", response_model=InvitationListResponse)
async def list_invitations(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> InvitationListResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.MEMBERS_VIEW)
    criteria = Invitation.company_id == context.company_id
    total = await session.scalar(select(func.count()).select_from(Invitation).where(criteria))
    invitations = await session.scalars(
        select(Invitation)
        .where(criteria)
        .order_by(Invitation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return InvitationListResponse(
        items=[invitation_response(item) for item in invitations],
        page=page,
        page_size=page_size,
        total=total or 0,
    )


@router.post("/{invitation_id}/resend-code", response_model=CreatedInvitationResponse)
async def resend_invitation_code(
    invitation_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> CreatedInvitationResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.MEMBERS_CREATE)
    invitation = await session.scalar(
        select(Invitation)
        .where(
            Invitation.company_id == context.company_id,
            Invitation.id == invitation_id,
        )
        .with_for_update()
    )
    if invitation is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="invitation_not_found",
            title="Invitation not found",
            detail="The invitation does not exist in the current company.",
        )
    if invitation.status != "pending":
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="invitation_not_pending",
            title="Invitation is not pending",
            detail="Only pending invitations can receive a new activation code.",
        )
    raw_token = token_urlsafe(48)
    invitation.token_hash = sha256(raw_token.encode("utf-8")).hexdigest()
    invitation.expires_at = datetime.now(UTC) + timedelta(days=7)
    await session.commit()
    await session.refresh(invitation)
    return CreatedInvitationResponse(
        **invitation_response(invitation).model_dump(),
        activation_token=raw_token,
    )


@router.get("/{invitation_id}", response_model=InvitationResponse)
async def get_invitation(
    invitation_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> InvitationResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.MEMBERS_VIEW)
    invitation = await session.scalar(
        select(Invitation).where(
            Invitation.company_id == context.company_id,
            Invitation.id == invitation_id,
        )
    )
    if invitation is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="invitation_not_found",
            title="Invitation not found",
            detail="The invitation does not exist in the current company.",
        )
    return invitation_response(invitation)


@activation_router.post("/activate", response_model=AuthTokenResponse)
async def activate_invitation(
    payload: ActivateInvitationRequest,
    session: DatabaseSession,
) -> AuthTokenResponse:
    token_hash = sha256(payload.activation_token.encode("utf-8")).hexdigest()
    invitation = await session.scalar(
        select(Invitation).where(Invitation.token_hash == token_hash).with_for_update()
    )
    now = datetime.now(UTC)
    if invitation is None or invitation.status != "pending" or invitation.expires_at <= now:
        raise ProblemError(
            status=status.HTTP_400_BAD_REQUEST,
            code="invitation_invalid",
            title="Invitation is invalid",
            detail="The invitation is expired, used, or invalid.",
        )
    if await session.scalar(select(User.id).where(User.email == invitation.email)) is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="account_already_exists",
            title="Account already exists",
            detail="Sign in to accept invitations for an existing account.",
        )
    user = User(
        email=invitation.email,
        full_name=invitation.full_name,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.flush()
    membership = CompanyMembership(
        company_id=invitation.company_id,
        user_id=user.id,
        role_code=invitation.role_code,
    )
    session.add(membership)
    await session.flush()
    session.add(
        EmployeeProfile(
            company_id=invitation.company_id,
            membership_id=membership.id,
            display_name=user.full_name,
        )
    )
    session.add(
        MembershipRole(
            company_id=invitation.company_id,
            membership_id=membership.id,
            role_code=invitation.role_code,
        )
    )
    await session.flush()
    invitation.status = "accepted"
    invitation.accepted_at = now
    company = await session.get(Company, invitation.company_id)
    if company is None:
        raise RuntimeError("Invitation company no longer exists")
    response = await issue_tokens(
        session=session,
        user=user,
        company=company,
        membership=membership,
    )
    await session.commit()
    return response
