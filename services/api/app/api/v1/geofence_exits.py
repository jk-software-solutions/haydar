from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.attendance import approved_device, distance_metres
from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    effective_permission_codes,
    require_membership_scope,
    require_permission,
    tenant_context,
    visible_membership_ids,
)
from app.core.config import get_settings
from app.core.errors import ProblemError
from app.db.session import get_session
from app.models.attendance import AttendanceRecord, GeofenceExitEvent, PermissionRequest
from app.models.devices import AuditLog
from app.models.identity import (
    CompanyMembership,
    MembershipBranchScope,
    MembershipDepartmentScope,
    MembershipGroupScope,
    MembershipRole,
)
from app.models.organization import Branch, EmployeeGroupMembership, EmployeeProfile
from app.models.workforce import Notification

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]
InstallationId = Annotated[UUID | None, Header(alias="X-Installation-ID")]


class GeofenceSampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: UUID
    observed_at: datetime
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    accuracy_m: int | None = Field(default=None, ge=0, le=10000)
    source: Literal["foreground_monitor", "foreground_service", "resume_check"]
    location_permission: Literal[
        "while_in_use", "always", "denied", "denied_forever", "service_disabled"
    ]

    @model_validator(mode="after")
    def validate_coordinates(self) -> Self:
        available = self.location_permission in {"while_in_use", "always"}
        coordinates = self.latitude is not None and self.longitude is not None
        if available and (not coordinates or self.accuracy_m is None):
            raise ValueError("coordinates and accuracy_m are required when location is available")
        if not available and (self.latitude is not None or self.longitude is not None):
            raise ValueError("coordinates must be omitted when location is unavailable")
        return self


class GeofenceReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["confirmed_unauthorized", "dismissed", "approved_exception"]
    comment: str = Field(min_length=3, max_length=2000)
    version: int = Field(ge=1)


class GeofenceExitResponse(BaseModel):
    id: UUID
    record_id: UUID
    membership_id: UUID
    branch_id: UUID
    shift_id: UUID
    status: str
    source: str
    location_permission: str
    first_detected_at: datetime
    detected_at: datetime
    latitude: Decimal | None
    longitude: Decimal | None
    accuracy_m: int | None
    distance_m: int | None
    consecutive_outside_samples: int
    grace_seconds: int
    permission_request_id: UUID | None
    reconfirmed_at: datetime | None
    reviewed_by_membership_id: UUID | None
    review_comment: str | None
    reviewed_at: datetime | None
    version: int


def response(item: GeofenceExitEvent) -> GeofenceExitResponse:
    return GeofenceExitResponse.model_validate(item, from_attributes=True)


async def open_record(
    session: AsyncSession, company_id: UUID, membership_id: UUID, record_id: UUID
) -> AttendanceRecord:
    item = await session.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.company_id == company_id,
            AttendanceRecord.id == record_id,
            AttendanceRecord.membership_id == membership_id,
            AttendanceRecord.checked_in_at.is_not(None),
            AttendanceRecord.checked_out_at.is_(None),
        )
    )
    if item is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="open_attendance_not_found",
            title="Open attendance not found",
            detail="The open attendance record is unavailable for this employee.",
        )
    return item


async def active_permission(
    session: AsyncSession, record: AttendanceRecord, observed_at: datetime
) -> PermissionRequest | None:
    item: PermissionRequest | None = await session.scalar(
        select(PermissionRequest).where(
            PermissionRequest.company_id == record.company_id,
            PermissionRequest.membership_id == record.membership_id,
            PermissionRequest.status == "approved",
            PermissionRequest.starts_at <= observed_at,
            PermissionRequest.ends_at >= observed_at,
        )
    )
    return item


async def notify_managers(
    session: AsyncSession, record: AttendanceRecord, event: GeofenceExitEvent
) -> None:
    candidate_ids = set(
        await session.scalars(
            select(MembershipRole.membership_id).where(
                MembershipRole.company_id == record.company_id,
                MembershipRole.role_code.in_(("OWNER", "HR_OFFICER")),
            )
        )
    )
    candidate_ids.update(
        await session.scalars(
            select(MembershipBranchScope.membership_id).where(
                MembershipBranchScope.company_id == record.company_id,
                MembershipBranchScope.branch_id == record.branch_id,
            )
        )
    )
    department_id = await session.scalar(
        select(EmployeeProfile.department_id).where(
            EmployeeProfile.company_id == record.company_id,
            EmployeeProfile.membership_id == record.membership_id,
        )
    )
    if department_id is not None:
        candidate_ids.update(
            await session.scalars(
                select(MembershipDepartmentScope.membership_id).where(
                    MembershipDepartmentScope.company_id == record.company_id,
                    MembershipDepartmentScope.department_id == department_id,
                )
            )
        )
    subject_groups = select(EmployeeGroupMembership.group_id).where(
        EmployeeGroupMembership.company_id == record.company_id,
        EmployeeGroupMembership.membership_id == record.membership_id,
    )
    candidate_ids.update(
        await session.scalars(
            select(MembershipGroupScope.membership_id).where(
                MembershipGroupScope.company_id == record.company_id,
                MembershipGroupScope.group_id.in_(subject_groups),
            )
        )
    )
    active_ids = set(
        await session.scalars(
            select(CompanyMembership.id).where(
                CompanyMembership.company_id == record.company_id,
                CompanyMembership.id.in_(candidate_ids),
                CompanyMembership.status == "active",
            )
        )
    )
    recipients = [
        member_id
        for member_id in active_ids
        if Permission.GEOFENCE_EXITS_VIEW.value
        in await effective_permission_codes(session, record.company_id, member_id)
    ]
    session.add_all(
        [
            Notification(
                company_id=record.company_id,
                membership_id=member_id,
                kind="geofence_exit_unauthorized",
                title="Unauthorized branch exit",
                body="An employee remained outside the branch geofence without permission.",
                target_type="geofence_exit_event",
                target_id=event.id,
                urgent=True,
            )
            for member_id in recipients
        ]
    )


@router.post("/report", response_model=GeofenceExitResponse, status_code=status.HTTP_201_CREATED)
async def report_geofence_sample(
    payload: GeofenceSampleRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    installation_id: InstallationId = None,
) -> GeofenceExitResponse:
    context = tenant_context(auth_session)
    device = await approved_device(session, context, installation_id)
    record = await open_record(
        session, context.company_id, context.membership.id, payload.record_id
    )
    now = datetime.now(UTC)
    observed_at = payload.observed_at.astimezone(UTC)
    if observed_at < now - timedelta(minutes=10) or observed_at > now + timedelta(minutes=2):
        raise ProblemError(
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="location_sample_stale",
            title="Location sample is stale",
            detail="Submit a current location observation.",
        )
    settings = get_settings()
    if payload.location_permission not in {"while_in_use", "always"}:
        item = GeofenceExitEvent(
            company_id=context.company_id,
            record_id=record.id,
            membership_id=record.membership_id,
            branch_id=record.branch_id,
            shift_id=record.shift_id,
            device_id=device.id,
            status="monitoring_unavailable",
            source=payload.source,
            location_permission=payload.location_permission,
            first_detected_at=observed_at,
            detected_at=observed_at,
            grace_seconds=settings.geofence_exit_grace_seconds,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return response(item)
    branch = await session.scalar(
        select(Branch).where(Branch.company_id == context.company_id, Branch.id == record.branch_id)
    )
    if branch is None or payload.latitude is None or payload.longitude is None:
        raise RuntimeError("Open attendance references an invalid branch")
    distance = distance_metres(
        payload.latitude, payload.longitude, branch.latitude, branch.longitude
    )
    active_event = await session.scalar(
        select(GeofenceExitEvent)
        .where(
            GeofenceExitEvent.company_id == context.company_id,
            GeofenceExitEvent.record_id == record.id,
            GeofenceExitEvent.status.in_(("observing", "unauthorized")),
        )
        .with_for_update()
    )
    if payload.accuracy_m is not None and payload.accuracy_m > settings.geofence_max_accuracy_m:
        item = GeofenceExitEvent(
            company_id=context.company_id,
            record_id=record.id,
            membership_id=record.membership_id,
            branch_id=record.branch_id,
            shift_id=record.shift_id,
            device_id=device.id,
            status="location_unreliable",
            source=payload.source,
            location_permission=payload.location_permission,
            first_detected_at=observed_at,
            detected_at=observed_at,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_m,
            distance_m=distance,
            grace_seconds=settings.geofence_exit_grace_seconds,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return response(item)
    if distance <= branch.geofence_radius_m:
        if active_event is not None:
            active_event.reconfirmed_at = observed_at
            active_event.detected_at = observed_at
            active_event.latitude = payload.latitude
            active_event.longitude = payload.longitude
            active_event.accuracy_m = payload.accuracy_m
            active_event.distance_m = distance
            active_event.version += 1
            if active_event.status == "observing":
                active_event.status = "reconfirmed"
            await session.commit()
            await session.refresh(active_event)
            return response(active_event)
        item = GeofenceExitEvent(
            company_id=context.company_id,
            record_id=record.id,
            membership_id=record.membership_id,
            branch_id=record.branch_id,
            shift_id=record.shift_id,
            device_id=device.id,
            status="inside",
            source=payload.source,
            location_permission=payload.location_permission,
            first_detected_at=observed_at,
            detected_at=observed_at,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_m,
            distance_m=distance,
            grace_seconds=settings.geofence_exit_grace_seconds,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return response(item)
    permission = await active_permission(session, record, observed_at)
    if permission is not None:
        if active_event is not None and active_event.status == "observing":
            active_event.status = "approved_exit"
            active_event.permission_request_id = permission.id
            active_event.detected_at = observed_at
            active_event.distance_m = distance
            active_event.version += 1
            await session.commit()
            await session.refresh(active_event)
            return response(active_event)
        item = GeofenceExitEvent(
            company_id=context.company_id,
            record_id=record.id,
            membership_id=record.membership_id,
            branch_id=record.branch_id,
            shift_id=record.shift_id,
            device_id=device.id,
            permission_request_id=permission.id,
            status="approved_exit",
            source=payload.source,
            location_permission=payload.location_permission,
            first_detected_at=observed_at,
            detected_at=observed_at,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_m,
            distance_m=distance,
            grace_seconds=settings.geofence_exit_grace_seconds,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return response(item)
    became_unauthorized = False
    if active_event is None:
        active_event = GeofenceExitEvent(
            company_id=context.company_id,
            record_id=record.id,
            membership_id=record.membership_id,
            branch_id=record.branch_id,
            shift_id=record.shift_id,
            device_id=device.id,
            status="observing",
            source=payload.source,
            location_permission=payload.location_permission,
            first_detected_at=observed_at,
            detected_at=observed_at,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_m,
            distance_m=distance,
            grace_seconds=settings.geofence_exit_grace_seconds,
        )
        session.add(active_event)
        await session.flush()
    else:
        active_event.detected_at = observed_at
        active_event.latitude = payload.latitude
        active_event.longitude = payload.longitude
        active_event.accuracy_m = payload.accuracy_m
        active_event.distance_m = distance
        active_event.consecutive_outside_samples += 1
        active_event.version += 1
        elapsed = (observed_at - active_event.first_detected_at).total_seconds()
        if (
            active_event.status == "observing"
            and active_event.consecutive_outside_samples >= settings.geofence_exit_min_samples
            and elapsed >= settings.geofence_exit_grace_seconds
        ):
            active_event.status = "unauthorized"
            became_unauthorized = True
    if became_unauthorized:
        await notify_managers(session, record, active_event)
        session.add(
            AuditLog(
                company_id=context.company_id,
                actor_membership_id=context.membership.id,
                action="geofence_exit.detected",
                target_type="geofence_exit_event",
                target_id=active_event.id,
                details={"distance_m": distance, "record_id": str(record.id)},
            )
        )
    await session.commit()
    await session.refresh(active_event)
    return response(active_event)


@router.get("", response_model=list[GeofenceExitResponse])
async def list_geofence_exit_events(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    event_status: Annotated[str | None, Query(alias="status")] = None,
    membership_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[GeofenceExitResponse]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.GEOFENCE_EXITS_VIEW)
    criteria = [GeofenceExitEvent.company_id == context.company_id]
    visible = await visible_membership_ids(session, context)
    if visible is not None:
        criteria.append(GeofenceExitEvent.membership_id.in_(visible))
    if membership_id is not None:
        await require_membership_scope(session, context, membership_id)
        criteria.append(GeofenceExitEvent.membership_id == membership_id)
    if event_status:
        criteria.append(GeofenceExitEvent.status == event_status)
    if date_from:
        criteria.append(
            GeofenceExitEvent.detected_at >= datetime.combine(date_from, datetime.min.time(), UTC)
        )
    if date_to:
        criteria.append(
            GeofenceExitEvent.detected_at
            < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), UTC)
        )
    items = await session.scalars(
        select(GeofenceExitEvent)
        .where(*criteria)
        .order_by(GeofenceExitEvent.detected_at.desc())
        .limit(2000)
    )
    return [response(item) for item in items]


@router.post("/{event_id}/review", response_model=GeofenceExitResponse)
async def review_geofence_exit_event(
    event_id: UUID,
    payload: GeofenceReviewRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> GeofenceExitResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.GEOFENCE_EXITS_MANAGE)
    item = await session.scalar(
        select(GeofenceExitEvent)
        .where(
            GeofenceExitEvent.company_id == context.company_id,
            GeofenceExitEvent.id == event_id,
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=status.HTTP_404_NOT_FOUND,
            code="geofence_exit_not_found",
            title="Geofence exit event not found",
            detail="The event does not exist in this company.",
        )
    await require_membership_scope(session, context, item.membership_id)
    if item.version != payload.version:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="concurrency_conflict",
            title="Geofence exit event changed",
            detail="Reload the event before reviewing it.",
        )
    before = item.status
    item.status = payload.decision
    item.reviewed_by_membership_id = context.membership.id
    item.review_comment = payload.comment
    item.reviewed_at = datetime.now(UTC)
    item.version += 1
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="geofence_exit.reviewed",
            target_type="geofence_exit_event",
            target_id=item.id,
            details={"before": before, "decision": payload.decision},
        )
    )
    await session.commit()
    await session.refresh(item)
    return response(item)
