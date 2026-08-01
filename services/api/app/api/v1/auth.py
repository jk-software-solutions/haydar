from datetime import UTC, datetime, timedelta
from re import sub
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.errors import ProblemError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.db.session import get_session
from app.models.identity import (
    Company,
    CompanyMembership,
    MembershipRole,
    RefreshSession,
    User,
)

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


class RegisterCompanyRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    owner_full_name: str = Field(min_length=2, max_length=160)
    owner_email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("owner_email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str


class CompanyResponse(BaseModel):
    id: UUID
    display_name: str


class SessionResponse(BaseModel):
    user: UserResponse
    company: CompanyResponse
    membership_id: UUID
    roles: list[str]


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    session: SessionResponse


def technical_name_from_display_name(display_name: str) -> str:
    candidate = sub(r"[^a-z0-9]+", "-", display_name.strip().lower()).strip("-")
    return candidate[:64] or "company"


async def unique_company_technical_name(session: AsyncSession, display_name: str) -> str:
    base = technical_name_from_display_name(display_name)
    candidate = base
    index = 2
    while True:
        exists = await session.scalar(select(Company.id).where(Company.technical_name == candidate))
        if exists is None:
            return candidate
        candidate = f"{base[:56]}-{index}"
        index += 1


def session_response(
    *,
    user: User,
    company: Company,
    membership: CompanyMembership,
) -> SessionResponse:
    return SessionResponse(
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
        company=CompanyResponse(id=company.id, display_name=company.display_name),
        membership_id=membership.id,
        roles=[membership.role_code],
    )


async def issue_tokens(
    *,
    session: AsyncSession,
    user: User,
    company: Company,
    membership: CompanyMembership,
) -> AuthTokenResponse:
    settings = get_settings()
    refresh_token = new_refresh_token()
    refresh_session = RefreshSession(
        user_id=user.id,
        company_id=company.id,
        membership_id=membership.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_days),
    )
    session.add(refresh_session)
    await session.flush()
    access_token = create_access_token(
        user_id=user.id,
        company_id=company.id,
        membership_id=membership.id,
        session_id=refresh_session.id,
    )
    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in_seconds=settings.jwt_access_token_minutes * 60,
        session=session_response(user=user, company=company, membership=membership),
    )


async def active_membership_for_user(
    session: AsyncSession,
    user_id: UUID,
) -> CompanyMembership | None:
    statement = (
        select(CompanyMembership)
        .options(selectinload(CompanyMembership.company), selectinload(CompanyMembership.user))
        .where(
            CompanyMembership.user_id == user_id,
            CompanyMembership.status == "active",
        )
        .order_by(CompanyMembership.created_at.asc())
    )
    result = await session.execute(statement)
    return result.scalars().first()


async def current_session(
    session: DatabaseSession,
    authorization: Annotated[str | None, Header()] = None,
) -> tuple[User, Company, CompanyMembership]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ProblemError(
            status=status.HTTP_401_UNAUTHORIZED,
            code="authentication_required",
            title="Authentication required",
            detail="A valid bearer access token is required.",
        )

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
        if payload.get("typ") != "access":
            raise jwt.InvalidTokenError("Unexpected token type")
        user_id = UUID(str(payload["sub"]))
        company_id = UUID(str(payload["company_id"]))
        membership_id = UUID(str(payload["membership_id"]))
        refresh_session_id = UUID(str(payload["sid"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise ProblemError(
            status=status.HTTP_401_UNAUTHORIZED,
            code="invalid_access_token",
            title="Invalid access token",
            detail="The access token is expired or invalid.",
        ) from exc

    statement = (
        select(CompanyMembership)
        .options(selectinload(CompanyMembership.company), selectinload(CompanyMembership.user))
        .where(
            CompanyMembership.id == membership_id,
            CompanyMembership.user_id == user_id,
            CompanyMembership.company_id == company_id,
            CompanyMembership.status == "active",
        )
    )
    membership = await session.scalar(statement)
    active_refresh_session = await session.scalar(
        select(RefreshSession.id).where(
            RefreshSession.id == refresh_session_id,
            RefreshSession.user_id == user_id,
            RefreshSession.company_id == company_id,
            RefreshSession.membership_id == membership_id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(UTC),
        )
    )
    if (
        membership is None
        or not membership.user.is_active
        or membership.company.status != "active"
        or active_refresh_session is None
    ):
        raise ProblemError(
            status=status.HTTP_401_UNAUTHORIZED,
            code="invalid_session",
            title="Invalid session",
            detail="The authenticated session is no longer active.",
        )
    return membership.user, membership.company, membership


CurrentAuthSession = Annotated[tuple[User, Company, CompanyMembership], Depends(current_session)]


@router.post("/register-company", response_model=AuthTokenResponse, status_code=201)
async def register_company(
    payload: RegisterCompanyRequest,
    session: DatabaseSession,
) -> AuthTokenResponse:
    existing_user = await session.scalar(select(User.id).where(User.email == payload.owner_email))
    if existing_user is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="email_already_registered",
            title="Email already registered",
            detail="Use login or another owner email.",
        )

    company = Company(
        display_name=payload.company_name.strip(),
        technical_name=await unique_company_technical_name(session, payload.company_name),
    )
    user = User(
        email=payload.owner_email,
        full_name=payload.owner_full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    session.add_all([company, user])
    await session.flush()
    membership = CompanyMembership(
        company_id=company.id,
        user_id=user.id,
        role_code="OWNER",
    )
    session.add(membership)
    await session.flush()
    session.add(
        MembershipRole(
            company_id=company.id,
            membership_id=membership.id,
            role_code="OWNER",
        )
    )
    await session.flush()
    response = await issue_tokens(
        session=session,
        user=user,
        company=company,
        membership=membership,
    )
    await session.commit()
    return response


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    payload: LoginRequest,
    session: DatabaseSession,
) -> AuthTokenResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise ProblemError(
            status=status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
            title="Invalid credentials",
            detail="The email or password is incorrect.",
        )

    membership = await active_membership_for_user(session, user.id)
    if membership is None:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="membership_required",
            title="Company membership required",
            detail="This user does not have an active company membership.",
        )

    response = await issue_tokens(
        session=session,
        user=user,
        company=membership.company,
        membership=membership,
    )
    await session.commit()
    return response


@router.get("/session", response_model=SessionResponse)
async def get_current_session(
    auth_session: CurrentAuthSession,
) -> SessionResponse:
    user, company, membership = auth_session
    return session_response(user=user, company=company, membership=membership)


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh(
    payload: RefreshRequest,
    session: DatabaseSession,
) -> AuthTokenResponse:
    refresh_hash = hash_refresh_token(payload.refresh_token)
    statement = select(RefreshSession).where(
        RefreshSession.refresh_token_hash == refresh_hash,
        RefreshSession.revoked_at.is_(None),
        RefreshSession.expires_at > datetime.now(UTC),
    )
    stored_session = await session.scalar(statement)
    if stored_session is None:
        raise ProblemError(
            status=status.HTTP_401_UNAUTHORIZED,
            code="invalid_refresh_token",
            title="Invalid refresh token",
            detail="The refresh token is expired, revoked or invalid.",
        )

    membership = await session.scalar(
        select(CompanyMembership)
        .options(selectinload(CompanyMembership.company), selectinload(CompanyMembership.user))
        .where(
            CompanyMembership.id == stored_session.membership_id,
            CompanyMembership.user_id == stored_session.user_id,
            CompanyMembership.company_id == stored_session.company_id,
            CompanyMembership.status == "active",
        )
    )
    if membership is None:
        raise ProblemError(
            status=status.HTTP_401_UNAUTHORIZED,
            code="invalid_session",
            title="Invalid session",
            detail="The refresh session is no longer active.",
        )

    stored_session.revoked_at = datetime.now(UTC)
    response = await issue_tokens(
        session=session,
        user=membership.user,
        company=membership.company,
        membership=membership,
    )
    await session.commit()
    return response


@router.post("/logout", status_code=204)
async def logout(
    payload: LogoutRequest,
    session: DatabaseSession,
) -> None:
    refresh_hash = hash_refresh_token(payload.refresh_token)
    stored_session = await session.scalar(
        select(RefreshSession).where(
            RefreshSession.refresh_token_hash == refresh_hash,
            RefreshSession.revoked_at.is_(None),
        )
    )
    if stored_session is not None:
        stored_session.revoked_at = datetime.now(UTC)
        await session.commit()
