from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    membership_scopes,
    require_group_scope,
    require_permission,
    require_unrestricted_scope,
    tenant_context,
)
from app.core.errors import ProblemError
from app.db.session import get_session
from app.models.devices import AuditLog
from app.models.identity import CompanyMembership
from app.models.organization import EmployeeGroupMembership, OrganizationGroup

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


class GroupCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=1000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class GroupUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=1000)
    is_active: bool
    version: int = Field(ge=1)


class GroupMembersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_ids: list[UUID] = Field(default_factory=list, max_length=2000)


class GroupResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str
    is_active: bool
    version: int
    membership_ids: list[UUID]


class GroupListResponse(BaseModel):
    items: list[GroupResponse]
    page: int
    page_size: int
    total: int


async def group_response(session: AsyncSession, item: OrganizationGroup) -> GroupResponse:
    membership_ids = list(
        await session.scalars(
            select(EmployeeGroupMembership.membership_id)
            .where(
                EmployeeGroupMembership.company_id == item.company_id,
                EmployeeGroupMembership.group_id == item.id,
            )
            .order_by(EmployeeGroupMembership.membership_id)
        )
    )
    return GroupResponse(
        id=item.id,
        code=item.code,
        name=item.name,
        description=item.description,
        is_active=item.is_active,
        version=item.version,
        membership_ids=membership_ids,
    )


async def scoped_group(
    session: AsyncSession, company_id: UUID, group_id: UUID
) -> OrganizationGroup:
    item = await session.scalar(
        select(OrganizationGroup).where(
            OrganizationGroup.company_id == company_id,
            OrganizationGroup.id == group_id,
        )
    )
    if item is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="group_not_found",
            title="Group not found",
            detail="The group does not exist in this company.",
        )
    return item


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> GroupResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_MANAGE)
    await require_unrestricted_scope(session, context)
    exists = await session.scalar(
        select(OrganizationGroup.id).where(
            OrganizationGroup.company_id == context.company_id,
            OrganizationGroup.code == payload.code,
        )
    )
    if exists is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="group_code_exists",
            title="Group code already exists",
            detail="Use a unique group code inside this company.",
        )
    item = OrganizationGroup(
        company_id=context.company_id,
        code=payload.code,
        name=payload.name.strip(),
        description=payload.description.strip(),
    )
    session.add(item)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="group.created",
            target_type="organization_group",
            target_id=item.id,
            details={"code": item.code},
        )
    )
    await session.commit()
    return await group_response(session, item)


@router.get("", response_model=GroupListResponse)
async def list_groups(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    include_inactive: bool = False,
) -> GroupListResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_VIEW)
    criteria = [OrganizationGroup.company_id == context.company_id]
    scopes = await membership_scopes(session, context)
    if not scopes.unrestricted:
        own_group_ids = set(
            await session.scalars(
                select(EmployeeGroupMembership.group_id).where(
                    EmployeeGroupMembership.company_id == context.company_id,
                    EmployeeGroupMembership.membership_id == context.membership.id,
                )
            )
        )
        criteria.append(OrganizationGroup.id.in_(scopes.group_ids | own_group_ids))
    if not include_inactive:
        criteria.append(OrganizationGroup.is_active.is_(True))
    total = int(
        await session.scalar(select(func.count()).select_from(OrganizationGroup).where(*criteria))
        or 0
    )
    rows = list(
        await session.scalars(
            select(OrganizationGroup)
            .where(*criteria)
            .order_by(OrganizationGroup.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return GroupListResponse(
        items=[await group_response(session, item) for item in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    payload: GroupUpdateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> GroupResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_MANAGE)
    await require_group_scope(session, context, group_id)
    item = await scoped_group(session, context.company_id, group_id)
    if item.version != payload.version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="version_conflict",
            title="Group changed",
            detail="Reload the group before saving again.",
        )
    before = {"name": item.name, "description": item.description, "is_active": item.is_active}
    item.name = payload.name.strip()
    item.description = payload.description.strip()
    item.is_active = payload.is_active
    item.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="group.updated",
            target_type="organization_group",
            target_id=item.id,
            details={
                "before": before,
                "after": {
                    "name": item.name,
                    "description": item.description,
                    "is_active": item.is_active,
                },
            },
        )
    )
    await session.commit()
    return await group_response(session, item)


@router.put("/{group_id}/members", response_model=GroupResponse)
async def replace_group_members(
    group_id: UUID,
    payload: GroupMembersRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> GroupResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEPARTMENTS_MANAGE)
    await require_group_scope(session, context, group_id)
    item = await scoped_group(session, context.company_id, group_id)
    requested = set(payload.membership_ids)
    found = set(
        await session.scalars(
            select(CompanyMembership.id).where(
                CompanyMembership.company_id == context.company_id,
                CompanyMembership.id.in_(requested),
                CompanyMembership.status == "active",
            )
        )
    )
    if found != requested:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="group_member_not_found",
            title="Group member not found",
            detail="Every group member must be active in this company.",
        )
    before = list(
        await session.scalars(
            select(EmployeeGroupMembership.membership_id).where(
                EmployeeGroupMembership.company_id == context.company_id,
                EmployeeGroupMembership.group_id == group_id,
            )
        )
    )
    await session.execute(
        delete(EmployeeGroupMembership).where(
            EmployeeGroupMembership.company_id == context.company_id,
            EmployeeGroupMembership.group_id == group_id,
        )
    )
    session.add_all(
        [
            EmployeeGroupMembership(
                company_id=context.company_id,
                group_id=group_id,
                membership_id=membership_id,
                assigned_by_membership_id=context.membership.id,
            )
            for membership_id in requested
        ]
    )
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="group.members_replaced",
            target_type="organization_group",
            target_id=item.id,
            details={
                "before": sorted(str(value) for value in before),
                "after": sorted(str(value) for value in requested),
            },
        )
    )
    await session.commit()
    return await group_response(session, item)
