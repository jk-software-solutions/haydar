from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    RoleCode,
    effective_permission_codes,
    membership_roles,
    tenant_context,
)
from app.core.errors import ProblemError
from app.db.session import get_session
from app.models.devices import AuditLog
from app.models.identity import (
    CompanyMembership,
    MembershipBranchScope,
    MembershipDepartmentScope,
    MembershipGroupScope,
    MembershipPermissionOverride,
    MembershipRole,
    PermissionDefinition,
)
from app.models.organization import Branch, Department, OrganizationGroup

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]
ASSIGNABLE_ROLES = {
    RoleCode.MANAGER,
    RoleCode.SUPERVISOR,
    RoleCode.HR_OFFICER,
    RoleCode.EMPLOYEE,
}


class PermissionCatalogItem(BaseModel):
    code: str
    description: str


class MemberAccessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_codes: list[RoleCode] = Field(min_length=1, max_length=4)
    permission_overrides: dict[str, bool] = Field(default_factory=dict)
    branch_ids: list[UUID] = Field(default_factory=list, max_length=500)
    department_ids: list[UUID] = Field(default_factory=list, max_length=500)
    group_ids: list[UUID] = Field(default_factory=list, max_length=500)


class MemberAccessResponse(BaseModel):
    membership_id: UUID
    role_codes: list[str]
    permission_overrides: dict[str, bool]
    effective_permissions: list[str]
    branch_ids: list[UUID]
    department_ids: list[UUID]
    group_ids: list[UUID]


async def require_owner(session: AsyncSession, auth_session: CurrentAuthSession) -> None:
    _user, company, membership = auth_session
    roles = await membership_roles(session, company.id, membership.id)
    if RoleCode.OWNER.value not in roles:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="owner_required",
            title="Company owner required",
            detail="Only a company owner can change member roles, permissions, and scopes.",
        )


async def scoped_membership(
    session: AsyncSession, company_id: UUID, membership_id: UUID
) -> CompanyMembership:
    membership = await session.scalar(
        select(CompanyMembership).where(
            CompanyMembership.company_id == company_id,
            CompanyMembership.id == membership_id,
        )
    )
    if membership is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="membership_not_found",
            title="Membership not found",
            detail="The membership does not exist in this company.",
        )
    return membership


async def member_access_response(
    session: AsyncSession, company_id: UUID, membership_id: UUID
) -> MemberAccessResponse:
    role_codes = await membership_roles(session, company_id, membership_id)
    override_rows = await session.execute(
        select(
            MembershipPermissionOverride.permission_code,
            MembershipPermissionOverride.allowed,
        ).where(
            MembershipPermissionOverride.company_id == company_id,
            MembershipPermissionOverride.membership_id == membership_id,
        )
    )
    branch_ids = list(
        await session.scalars(
            select(MembershipBranchScope.branch_id).where(
                MembershipBranchScope.company_id == company_id,
                MembershipBranchScope.membership_id == membership_id,
            )
        )
    )
    department_ids = list(
        await session.scalars(
            select(MembershipDepartmentScope.department_id).where(
                MembershipDepartmentScope.company_id == company_id,
                MembershipDepartmentScope.membership_id == membership_id,
            )
        )
    )
    group_ids = list(
        await session.scalars(
            select(MembershipGroupScope.group_id).where(
                MembershipGroupScope.company_id == company_id,
                MembershipGroupScope.membership_id == membership_id,
            )
        )
    )
    return MemberAccessResponse(
        membership_id=membership_id,
        role_codes=role_codes,
        permission_overrides={code: allowed for code, allowed in override_rows},
        effective_permissions=await effective_permission_codes(session, company_id, membership_id),
        branch_ids=sorted(branch_ids),
        department_ids=sorted(department_ids),
        group_ids=sorted(group_ids),
    )


@router.get("/access-catalog", response_model=list[PermissionCatalogItem])
async def access_catalog(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[PermissionCatalogItem]:
    await require_owner(session, auth_session)
    rows = await session.scalars(select(PermissionDefinition).order_by(PermissionDefinition.code))
    return [PermissionCatalogItem(code=item.code, description=item.description) for item in rows]


@router.get("/access", response_model=list[MemberAccessResponse])
async def list_member_access(
    auth_session: CurrentAuthSession, session: DatabaseSession
) -> list[MemberAccessResponse]:
    _user, company, _membership = auth_session
    await require_owner(session, auth_session)
    member_ids = list(
        await session.scalars(
            select(CompanyMembership.id)
            .where(CompanyMembership.company_id == company.id)
            .order_by(CompanyMembership.created_at)
        )
    )
    return [
        await member_access_response(session, company.id, membership_id)
        for membership_id in member_ids
    ]


@router.get("/{membership_id}/access", response_model=MemberAccessResponse)
async def get_member_access(
    membership_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> MemberAccessResponse:
    context = tenant_context(auth_session)
    await require_owner(session, auth_session)
    await scoped_membership(session, context.company_id, membership_id)
    return await member_access_response(session, context.company_id, membership_id)


@router.put("/{membership_id}/access", response_model=MemberAccessResponse)
async def update_member_access(
    membership_id: UUID,
    payload: MemberAccessUpdate,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> MemberAccessResponse:
    context = tenant_context(auth_session)
    await require_owner(session, auth_session)
    target = await scoped_membership(session, context.company_id, membership_id)
    existing_roles = set(await membership_roles(session, context.company_id, membership_id))
    if RoleCode.OWNER.value in existing_roles or membership_id == context.membership.id:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="owner_access_immutable",
            title="Owner access cannot be changed",
            detail="Use a dedicated ownership-transfer process to change owner access.",
        )
    role_codes = set(payload.role_codes)
    if not role_codes or not role_codes.issubset(ASSIGNABLE_ROLES):
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="role_not_assignable",
            title="Role is not assignable",
            detail="Assign only manager, supervisor, HR officer, or employee roles.",
        )
    known_permissions = set(await session.scalars(select(PermissionDefinition.code)))
    unknown_permissions = set(payload.permission_overrides).difference(known_permissions)
    if unknown_permissions:
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="permission_unknown",
            title="Permission is unknown",
            detail=f"Unknown permission codes: {', '.join(sorted(unknown_permissions))}.",
        )
    await _validate_targets(session, context.company_id, Branch, payload.branch_ids, "branch")
    await _validate_targets(
        session, context.company_id, Department, payload.department_ids, "department"
    )
    await _validate_targets(
        session, context.company_id, OrganizationGroup, payload.group_ids, "group"
    )
    before = await member_access_response(session, context.company_id, membership_id)
    for model in (
        MembershipPermissionOverride,
        MembershipBranchScope,
        MembershipDepartmentScope,
        MembershipGroupScope,
        MembershipRole,
    ):
        await session.execute(
            delete(model).where(
                model.company_id == context.company_id,
                model.membership_id == membership_id,
            )
        )
    ordered_roles = sorted(code.value for code in role_codes)
    target.role_code = ordered_roles[0]
    target.version += 1
    session.add_all(
        [
            MembershipRole(
                company_id=context.company_id,
                membership_id=membership_id,
                role_code=role,
            )
            for role in ordered_roles
        ]
        + [
            MembershipPermissionOverride(
                company_id=context.company_id,
                membership_id=membership_id,
                permission_code=code,
                allowed=allowed,
                updated_by_membership_id=context.membership.id,
            )
            for code, allowed in payload.permission_overrides.items()
        ]
        + [
            MembershipBranchScope(
                company_id=context.company_id,
                membership_id=membership_id,
                branch_id=item_id,
            )
            for item_id in set(payload.branch_ids)
        ]
        + [
            MembershipDepartmentScope(
                company_id=context.company_id,
                membership_id=membership_id,
                department_id=item_id,
            )
            for item_id in set(payload.department_ids)
        ]
        + [
            MembershipGroupScope(
                company_id=context.company_id,
                membership_id=membership_id,
                group_id=item_id,
            )
            for item_id in set(payload.group_ids)
        ]
    )
    await session.flush()
    after = await member_access_response(session, context.company_id, membership_id)
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="membership.access_updated",
            target_type="company_membership",
            target_id=membership_id,
            details={
                "before": before.model_dump(mode="json"),
                "after": after.model_dump(mode="json"),
            },
        )
    )
    await session.commit()
    return after


async def _validate_targets(
    session: AsyncSession,
    company_id: UUID,
    model: type[Branch] | type[Department] | type[OrganizationGroup],
    target_ids: list[UUID],
    target_name: str,
) -> None:
    requested = set(target_ids)
    if not requested:
        return
    found = set(
        await session.scalars(
            select(model.id).where(model.company_id == company_id, model.id.in_(requested))
        )
    )
    if found != requested:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code=f"{target_name}_not_found",
            title=f"{target_name.title()} not found",
            detail=f"Every {target_name} scope must belong to this company.",
        )
