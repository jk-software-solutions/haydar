from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    require_membership_scope,
    require_permission,
    tenant_context,
    visible_membership_ids,
)
from app.core.errors import ProblemError
from app.db.session import get_session
from app.models.devices import AuditLog, Device, DeviceChangeRequest

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]


class RegisterDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    installation_id: UUID
    platform: str = Field(pattern="^(android|ios)$")
    device_name: str = Field(min_length=2, max_length=160)
    public_key: str | None = Field(default=None, min_length=32, max_length=8192)
    reason: str | None = Field(default=None, max_length=1000)


class DeviceResponse(BaseModel):
    id: UUID
    installation_id: UUID
    platform: str
    device_name: str
    status: str
    approved_at: datetime | None
    revoked_at: datetime | None


class DeviceRegistrationResponse(BaseModel):
    device: DeviceResponse
    change_request_id: UUID | None
    requires_approval: bool


class ReviewDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment: str | None = Field(default=None, max_length=1000)


class DeviceChangeResponse(BaseModel):
    id: UUID
    membership_id: UUID
    current_device_id: UUID | None
    requested_device_id: UUID
    reason: str
    status: str
    reviewed_at: datetime | None


class DeviceChangeListResponse(BaseModel):
    items: list[DeviceChangeResponse]
    page: int
    page_size: int
    total: int


def device_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        installation_id=device.installation_id,
        platform=device.platform,
        device_name=device.device_name,
        status=device.status,
        approved_at=device.approved_at,
        revoked_at=device.revoked_at,
    )


def change_response(change: DeviceChangeRequest) -> DeviceChangeResponse:
    return DeviceChangeResponse(
        id=change.id,
        membership_id=change.membership_id,
        current_device_id=change.current_device_id,
        requested_device_id=change.requested_device_id,
        reason=change.reason,
        status=change.status,
        reviewed_at=change.reviewed_at,
    )


@router.post("/register", response_model=DeviceRegistrationResponse, status_code=201)
async def register_device(
    payload: RegisterDeviceRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DeviceRegistrationResponse:
    context = tenant_context(auth_session)
    existing = await session.scalar(
        select(Device).where(
            Device.company_id == context.company_id,
            Device.installation_id == payload.installation_id,
        )
    )
    if existing is not None:
        if existing.membership_id != context.membership.id:
            raise ProblemError(
                status=status.HTTP_409_CONFLICT,
                code="device_already_registered",
                title="Device already registered",
                detail="This installation belongs to another company member.",
            )
        pending = await session.scalar(
            select(DeviceChangeRequest.id).where(
                DeviceChangeRequest.company_id == context.company_id,
                DeviceChangeRequest.requested_device_id == existing.id,
                DeviceChangeRequest.status == "pending",
            )
        )
        return DeviceRegistrationResponse(
            device=device_response(existing),
            change_request_id=pending,
            requires_approval=existing.status == "pending",
        )

    current = await session.scalar(
        select(Device)
        .where(
            Device.company_id == context.company_id,
            Device.membership_id == context.membership.id,
            Device.status == "approved",
        )
        .with_for_update()
    )
    change_reason = payload.reason.strip() if payload.reason else ""
    if current is not None and len(change_reason) < 5:
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="device_change_reason_required",
            title="Device change reason required",
            detail="Explain why the approved device must be changed.",
        )
    pending_request = await session.scalar(
        select(DeviceChangeRequest.id).where(
            DeviceChangeRequest.company_id == context.company_id,
            DeviceChangeRequest.membership_id == context.membership.id,
            DeviceChangeRequest.status == "pending",
        )
    )
    if pending_request is not None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="device_change_pending",
            title="Device change already pending",
            detail="A manager must review the existing device change request first.",
        )

    now = datetime.now(UTC)
    device = Device(
        company_id=context.company_id,
        membership_id=context.membership.id,
        installation_id=payload.installation_id,
        platform=payload.platform,
        device_name=payload.device_name.strip(),
        public_key=payload.public_key,
        status="approved" if current is None else "pending",
        approved_at=now if current is None else None,
        approved_by_membership_id=context.membership.id if current is None else None,
        last_seen_at=now,
    )
    session.add(device)
    await session.flush()
    change: DeviceChangeRequest | None = None
    if current is not None:
        change = DeviceChangeRequest(
            company_id=context.company_id,
            membership_id=context.membership.id,
            current_device_id=current.id,
            requested_device_id=device.id,
            reason=change_reason,
        )
        session.add(change)
        await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="device.change_requested" if change else "device.first_approved",
            target_type="device",
            target_id=device.id,
            details={"installation_id": str(device.installation_id)},
        )
    )
    await session.commit()
    return DeviceRegistrationResponse(
        device=device_response(device),
        change_request_id=change.id if change else None,
        requires_approval=change is not None,
    )


@router.get("/me", response_model=list[DeviceResponse])
async def list_my_devices(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> list[DeviceResponse]:
    context = tenant_context(auth_session)
    devices = await session.scalars(
        select(Device)
        .where(
            Device.company_id == context.company_id,
            Device.membership_id == context.membership.id,
        )
        .order_by(Device.created_at.desc())
    )
    return [device_response(device) for device in devices]


@router.get("/change-requests", response_model=DeviceChangeListResponse)
async def list_device_changes(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    request_status: Annotated[str | None, Query(alias="status")] = "pending",
) -> DeviceChangeListResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEVICES_VIEW)
    criteria = [DeviceChangeRequest.company_id == context.company_id]
    visible = await visible_membership_ids(session, context)
    if visible is not None:
        criteria.append(DeviceChangeRequest.membership_id.in_(visible))
    if request_status:
        criteria.append(DeviceChangeRequest.status == request_status)
    total = await session.scalar(
        select(func.count()).select_from(DeviceChangeRequest).where(*criteria)
    )
    changes = await session.scalars(
        select(DeviceChangeRequest)
        .where(*criteria)
        .order_by(DeviceChangeRequest.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return DeviceChangeListResponse(
        items=[change_response(change) for change in changes],
        page=page,
        page_size=page_size,
        total=total or 0,
    )


@router.post("/change-requests/{request_id}/approve", response_model=DeviceChangeResponse)
async def approve_device_change(
    request_id: UUID,
    payload: ReviewDeviceRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DeviceChangeResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEVICES_MANAGE)
    change = await session.scalar(
        select(DeviceChangeRequest)
        .where(
            DeviceChangeRequest.company_id == context.company_id,
            DeviceChangeRequest.id == request_id,
            DeviceChangeRequest.status == "pending",
        )
        .with_for_update()
    )
    if change is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="device_change_not_found",
            title="Device change not found",
            detail="No pending device change exists in the current company.",
        )
    await require_membership_scope(session, context, change.membership_id)
    devices = await session.scalars(
        select(Device)
        .where(
            Device.company_id == context.company_id,
            Device.id.in_([change.current_device_id, change.requested_device_id]),
        )
        .with_for_update()
    )
    by_id = {device.id: device for device in devices}
    requested = by_id.get(change.requested_device_id)
    if requested is None or requested.membership_id != change.membership_id:
        raise RuntimeError("Device change request references an invalid requested device")
    now = datetime.now(UTC)
    current = by_id.get(change.current_device_id) if change.current_device_id else None
    if current is not None:
        current.status = "revoked"
        current.revoked_at = now
        await session.flush()
    requested.status = "approved"
    requested.approved_at = now
    requested.approved_by_membership_id = context.membership.id
    change.status = "approved"
    change.reviewed_by_membership_id = context.membership.id
    change.review_comment = payload.comment
    change.reviewed_at = now
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="device.change_approved",
            target_type="device_change_request",
            target_id=change.id,
            details={
                "old_device_id": str(current.id) if current else None,
                "new_device_id": str(requested.id),
            },
        )
    )
    await session.commit()
    return change_response(change)


@router.post("/change-requests/{request_id}/reject", response_model=DeviceChangeResponse)
async def reject_device_change(
    request_id: UUID,
    payload: ReviewDeviceRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> DeviceChangeResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.DEVICES_MANAGE)
    change = await session.scalar(
        select(DeviceChangeRequest)
        .where(
            DeviceChangeRequest.company_id == context.company_id,
            DeviceChangeRequest.id == request_id,
            DeviceChangeRequest.status == "pending",
        )
        .with_for_update()
    )
    if change is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="device_change_not_found",
            title="Device change not found",
            detail="No pending device change exists in the current company.",
        )
    await require_membership_scope(session, context, change.membership_id)
    requested = await session.scalar(
        select(Device).where(
            Device.company_id == context.company_id,
            Device.id == change.requested_device_id,
        )
    )
    now = datetime.now(UTC)
    if requested is not None:
        requested.status = "revoked"
        requested.revoked_at = now
    change.status = "rejected"
    change.reviewed_by_membership_id = context.membership.id
    change.review_comment = payload.comment
    change.reviewed_at = now
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="device.change_rejected",
            target_type="device_change_request",
            target_id=change.id,
            details={"requested_device_id": str(change.requested_device_id)},
        )
    )
    await session.commit()
    return change_response(change)
