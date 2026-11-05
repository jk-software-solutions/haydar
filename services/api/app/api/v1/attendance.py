from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
from math import asin, cos, radians, sin, sqrt
from secrets import token_urlsafe
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import CurrentAuthSession
from app.core.authorization import (
    Permission,
    TenantContext,
    require_branch_scope,
    require_group_scope,
    require_membership_scope,
    require_permission,
    require_unrestricted_scope,
    tenant_context,
    visible_membership_ids,
)
from app.core.errors import ProblemError
from app.core.subscription_catalog import active_subscription
from app.db.session import get_session
from app.models.attendance import (
    AttendanceEvent,
    AttendanceRecord,
    BranchQrToken,
    BranchQrTokenUse,
    PermissionRequest,
    PresenceRecipient,
    PresenceRequest,
)
from app.models.devices import AuditLog, Device
from app.models.identity import CompanyMembership, User
from app.models.organization import (
    Branch,
    EmployeeBranchAssignment,
    EmployeeGroupMembership,
    EmployeeProfile,
    Shift,
    ShiftAssignment,
    ShiftException,
)
from app.models.workforce import LeaveRequest, Notification
from app.services.file_access import require_owned_attachment
from app.services.idempotency import IdempotencyKey, begin_idempotency, complete_idempotency
from app.services.notification_actor import membership_actor_name

router = APIRouter()
permissions_router = APIRouter()
presence_router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_session)]
InstallationId = Annotated[UUID | None, Header(alias="X-Installation-ID")]


class AttendanceActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["gps", "qr", "wifi"] = "gps"
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    qr_token: str | None = Field(default=None, min_length=20, max_length=200)
    wifi_ssid: str | None = Field(default=None, min_length=1, max_length=128)
    wifi_bssid: str | None = Field(
        default=None, pattern=r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
    )
    biometric_confirmed: bool = False

    @model_validator(mode="after")
    def require_method_evidence(self) -> "AttendanceActionRequest":
        if self.method == "qr" and self.qr_token is None:
            raise ValueError("qr_token is required for QR attendance")
        if self.method == "wifi" and (
            self.wifi_ssid is None or self.wifi_bssid is None
        ):
            raise ValueError(
                "wifi_ssid and wifi_bssid are required for Wi-Fi attendance"
            )
        return self


def accepted_biometric_declaration(
    context: TenantContext, payload: AttendanceActionRequest
) -> bool:
    policy = context.company.attendance_biometric_policy
    if policy == "required" and not payload.biometric_confirmed:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="biometric_confirmation_required",
            title="Biometric confirmation required",
            detail="Company policy requires local biometric confirmation for attendance.",
        )
    return policy != "disabled" and payload.biometric_confirmed


class AttendanceRecordResponse(BaseModel):
    id: UUID
    membership_id: UUID
    branch_id: UUID
    shift_id: UUID
    work_date: date
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    checked_in_at: datetime | None
    checked_out_at: datetime | None
    status: str
    check_in_method: str | None
    check_out_method: str | None
    late_minutes: int
    early_departure_minutes: int
    worked_minutes: int
    is_manual: bool
    review_status: str
    version: int
    # These labels are populated for manager/company attendance views. They
    # remain optional so employee/check-in responses keep their lean shape.
    employee_name: str | None = None
    employee_email: str | None = None
    branch_name: str | None = None
    shift_name: str | None = None


class AttendanceLocationEventResponse(BaseModel):
    """A location-bearing attendance event for the employee/manager map view."""

    id: UUID
    event_type: str
    method: str
    occurred_at: datetime
    latitude: Decimal | None
    longitude: Decimal | None
    distance_m: int | None
    branch_name: str
    branch_latitude: Decimal
    branch_longitude: Decimal
    geofence_radius_m: int
    employee_name: str | None


class ManualAttendanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: UUID
    branch_id: UUID
    shift_id: UUID
    work_date: date
    checked_in_at: datetime
    checked_out_at: datetime | None = None
    reason: str = Field(min_length=5, max_length=2000)
    attachment_file_id: UUID | None = None

    @model_validator(mode="after")
    def validate_times(self) -> "ManualAttendanceRequest":
        if self.checked_out_at is not None and self.checked_out_at <= self.checked_in_at:
            raise ValueError("checked_out_at must be after checked_in_at")
        return self


class CorrectAttendanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    checked_in_at: datetime | None = None
    checked_out_at: datetime | None = None
    status: str | None = Field(default=None, max_length=32)
    reason: str = Field(min_length=5, max_length=2000)
    attachment_file_id: UUID | None = None


class CreateQrRequest(BaseModel):
    branch_id: UUID
    valid_for_seconds: int = Field(default=120, ge=30, le=900)


class QrTokenResponse(BaseModel):
    id: UUID
    token: str
    branch_id: UUID
    expires_at: datetime


class QrTokenSummaryResponse(BaseModel):
    id: UUID
    branch_id: UUID
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class PermissionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: Literal["one_hour", "multiple_hours", "custom", "until_shift_end"]
    starts_at: datetime
    ends_at: datetime | None = None
    reason: str = Field(min_length=3, max_length=2000)
    attachment_file_id: UUID | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "PermissionCreateRequest":
        if self.request_type == "until_shift_end":
            return self
        if self.ends_at is None:
            raise ValueError("ends_at is required unless request_type is until_shift_end")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.ends_at - self.starts_at > timedelta(hours=24):
            raise ValueError("permission duration cannot exceed 24 hours")
        return self


class PermissionReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str | None = Field(default=None, max_length=2000)


class PermissionResponse(BaseModel):
    id: UUID
    membership_id: UUID
    request_type: str
    starts_at: datetime
    ends_at: datetime
    reason: str
    attachment_file_id: UUID | None
    status: str
    review_comment: str | None
    reviewed_at: datetime | None
    created_at: datetime
    employee_name: str | None = None
    employee_email: str | None = None


class PresenceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_ids: list[UUID] = Field(default_factory=list, max_length=500)
    branch_id: UUID | None = None
    group_id: UUID | None = None
    message: str = Field(default="Confirm your presence", min_length=2, max_length=500)
    deadline_seconds: int = Field(default=300, ge=30, le=3600)

    @model_validator(mode="after")
    def require_target(self) -> "PresenceCreateRequest":
        if not self.membership_ids and self.branch_id is None and self.group_id is None:
            raise ValueError("membership_ids, branch_id, or group_id is required")
        return self


class PresenceRespondRequest(BaseModel):
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    note: str | None = Field(default=None, max_length=500)


class PresenceResponse(BaseModel):
    id: UUID
    request_id: UUID
    membership_id: UUID
    message: str
    deadline_at: datetime
    status: str
    responded_at: datetime | None
    distance_m: int | None
    note: str | None


def record_response(record: AttendanceRecord) -> AttendanceRecordResponse:
    return AttendanceRecordResponse.model_validate(record, from_attributes=True)


def manager_record_response(
    record: AttendanceRecord,
    *,
    employee_name: str | None,
    employee_email: str | None,
    branch_name: str | None,
    shift_name: str | None,
) -> AttendanceRecordResponse:
    response = record_response(record)
    response.employee_name = employee_name
    response.employee_email = employee_email
    response.branch_name = branch_name
    response.shift_name = shift_name
    return response


def permission_response(
    item: PermissionRequest,
    *,
    employee_name: str | None = None,
    employee_email: str | None = None,
) -> PermissionResponse:
    response = PermissionResponse.model_validate(item, from_attributes=True)
    response.employee_name = employee_name
    response.employee_email = employee_email
    return response


async def permission_employee_details(
    session: AsyncSession,
    company_id: UUID,
    membership_ids: set[UUID],
) -> dict[UUID, tuple[str | None, str]]:
    if not membership_ids:
        return {}
    rows = await session.execute(
        select(
            CompanyMembership.id,
            EmployeeProfile.display_name,
            User.full_name,
            User.email,
        )
        .join(User, User.id == CompanyMembership.user_id)
        .outerjoin(
            EmployeeProfile,
            and_(
                EmployeeProfile.company_id == CompanyMembership.company_id,
                EmployeeProfile.membership_id == CompanyMembership.id,
            ),
        )
        .where(
            CompanyMembership.company_id == company_id,
            CompanyMembership.id.in_(membership_ids),
        )
    )
    return {
        membership_id: (display_name or full_name, email)
        for membership_id, display_name, full_name, email in rows
    }


def distance_metres(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> int:
    earth_radius_m = 6_371_000
    phi1, phi2 = radians(float(lat1)), radians(float(lat2))
    delta_phi = radians(float(lat2 - lat1))
    delta_lambda = radians(float(lon2 - lon1))
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    return round(earth_radius_m * 2 * asin(sqrt(a)))


def qr_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def parse_shift_time(value: object) -> time | None:
    if isinstance(value, time):
        return value
    if not isinstance(value, str):
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def configured_shift_periods(shift: Shift) -> list[tuple[time, time]]:
    recurrence = shift.recurrence if isinstance(shift.recurrence, dict) else {}
    raw_periods = recurrence.get("periods")
    periods: list[tuple[time, time]] = []
    if isinstance(raw_periods, list):
        for item in raw_periods:
            if not isinstance(item, dict):
                continue
            start_time = parse_shift_time(item.get("start_time"))
            end_time = parse_shift_time(item.get("end_time"))
            if start_time is not None and end_time is not None:
                periods.append((start_time, end_time))
    return periods or [(shift.start_time, shift.end_time)]


def shift_requires_location(shift: Shift) -> bool:
    recurrence = shift.recurrence if isinstance(shift.recurrence, dict) else {}
    return recurrence.get("location_policy") != "location_not_required"


def remote_period_is_closed(shift: Shift, now: datetime, scheduled_end: datetime) -> bool:
    """Return whether a locationless shift must reject another check-in."""

    return not shift_requires_location(shift) and now >= scheduled_end


def period_window(
    work_date: date,
    start_time: time,
    end_time: time,
    zone: ZoneInfo,
) -> tuple[datetime, datetime]:
    local_start = datetime.combine(work_date, start_time, zone)
    end_date = work_date + timedelta(days=1) if end_time <= start_time else work_date
    local_end = datetime.combine(end_date, end_time, zone)
    return local_start, local_end


def active_shift_window(
    shift: Shift, work_date: date, local_now: datetime, zone: ZoneInfo
) -> tuple[datetime, datetime]:
    windows = [
        period_window(work_date, start, end, zone)
        for start, end in configured_shift_periods(shift)
    ]
    for local_start, local_end in windows:
        if local_start <= local_now <= local_end:
            return local_start, local_end
    future_windows = [window for window in windows if local_now <= window[1]]
    if future_windows:
        return min(future_windows, key=lambda window: window[0])
    return windows[-1]


async def approved_device(
    session: AsyncSession, context: TenantContext, installation_id: UUID | None
) -> Device:
    if installation_id is None:
        raise ProblemError(
            status=status.HTTP_400_BAD_REQUEST,
            code="installation_id_required",
            title="Installation ID required",
            detail="Attendance operations require X-Installation-ID.",
        )
    device = await session.scalar(
        select(Device).where(
            Device.company_id == context.company_id,
            Device.membership_id == context.membership.id,
            Device.installation_id == installation_id,
            Device.status == "approved",
            Device.revoked_at.is_(None),
        )
    )
    if device is None:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="device_not_approved",
            title="Device is not approved",
            detail="Use the employee's currently approved device.",
        )
    device.last_seen_at = datetime.now(UTC)
    return device


async def active_branch_and_shift(
    session: AsyncSession, context: TenantContext, now: datetime
) -> tuple[Branch, Shift, date, datetime, datetime]:
    if context.company.status not in {"active", "trial"}:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="company_inactive",
            title="Company is inactive",
            detail="Attendance is unavailable while the company account is inactive.",
        )
    if await active_subscription(session, context.company_id) is None:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="subscription_inactive",
            title="Subscription is inactive",
            detail="Attendance requires an active subscription or trial.",
        )
    profile = await session.scalar(
        select(EmployeeProfile).where(
            EmployeeProfile.company_id == context.company_id,
            EmployeeProfile.membership_id == context.membership.id,
            EmployeeProfile.attendance_enabled.is_(True),
        )
    )
    if profile is None:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="attendance_disabled",
            title="Attendance is disabled",
            detail="The employee profile is inactive or not configured for attendance.",
        )
    current_date = now.date()
    assignment = await session.scalar(
        select(EmployeeBranchAssignment)
        .where(
            EmployeeBranchAssignment.company_id == context.company_id,
            EmployeeBranchAssignment.membership_id == context.membership.id,
            EmployeeBranchAssignment.effective_from <= current_date,
            or_(
                EmployeeBranchAssignment.effective_to.is_(None),
                EmployeeBranchAssignment.effective_to >= current_date,
            ),
        )
        .order_by(EmployeeBranchAssignment.effective_from.desc())
    )
    if assignment is None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="branch_not_assigned",
            title="Branch not assigned",
            detail="Assign the employee to an active branch before attendance.",
        )
    branch = await session.scalar(
        select(Branch).where(
            Branch.company_id == context.company_id,
            Branch.id == assignment.branch_id,
            Branch.is_active.is_(True),
        )
    )
    if branch is None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="branch_inactive",
            title="Branch is inactive",
            detail="The assigned branch is not active.",
        )
    shift_assignment = await session.scalar(
        select(ShiftAssignment)
        .where(
            ShiftAssignment.company_id == context.company_id,
            or_(
                ShiftAssignment.membership_id == context.membership.id,
                and_(
                    ShiftAssignment.membership_id.is_(None),
                    ShiftAssignment.branch_id == branch.id,
                ),
            ),
            ShiftAssignment.effective_from <= current_date,
            or_(
                ShiftAssignment.effective_to.is_(None), ShiftAssignment.effective_to >= current_date
            ),
        )
        .order_by(
            ShiftAssignment.membership_id.is_not(None).desc(), ShiftAssignment.effective_from.desc()
        )
    )
    if shift_assignment is None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="shift_not_assigned",
            title="Shift not assigned",
            detail="Assign the employee or branch to an active shift before attendance.",
        )
    shift = await session.scalar(
        select(Shift).where(
            Shift.company_id == context.company_id,
            Shift.id == shift_assignment.shift_id,
            Shift.is_active.is_(True),
        )
    )
    if shift is None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="shift_inactive",
            title="Shift is inactive",
            detail="The assigned shift is not active.",
        )
    zone = ZoneInfo(branch.timezone)
    local_now = now.astimezone(zone)
    work_date = local_now.date()
    local_time = local_now.timetz().replace(tzinfo=None)
    if any(
        end_time <= start_time and local_time <= end_time
        for start_time, end_time in configured_shift_periods(shift)
    ):
        work_date -= timedelta(days=1)
    exception = await session.scalar(
        select(ShiftException).where(
            ShiftException.company_id == context.company_id,
            ShiftException.shift_id == shift.id,
            ShiftException.exception_date == work_date,
        )
    )
    if exception is not None and not exception.is_working_day:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="shift_not_working_today",
            title="No scheduled shift",
            detail="The shift has a non-working exception for this date.",
        )
    if exception is None and work_date.weekday() not in shift.working_days:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="shift_not_working_today",
            title="No scheduled shift",
            detail="The employee has no scheduled shift for this date.",
        )
    if exception and exception.override_start_time and exception.override_end_time:
        local_start, local_end = period_window(
            work_date,
            exception.override_start_time,
            exception.override_end_time,
            zone,
        )
    else:
        local_start, local_end = active_shift_window(shift, work_date, local_now, zone)
    return branch, shift, work_date, local_start.astimezone(UTC), local_end.astimezone(UTC)


async def validate_location_and_qr(
    session: AsyncSession,
    context: TenantContext,
    branch: Branch,
    payload: AttendanceActionRequest,
    now: datetime,
    action: Literal["check_in", "check_out"],
    location_required: bool = True,
) -> int:
    subscription = await active_subscription(session, context.company_id)
    if subscription is None:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="subscription_inactive",
            title="Subscription is inactive",
            detail="Attendance requires an active subscription or trial.",
        )
    _item, plan = subscription
    if not bool(plan.features.get(payload.method, False)):
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="subscription_feature_unavailable",
            title="Attendance method unavailable",
            detail=f"The {payload.method} method is not included in the current plan.",
        )
    if payload.method == "wifi":
        configured = (branch.working_hours or {}).get("wifi_networks", [])
        ssid = (payload.wifi_ssid or "").strip()
        bssid = (payload.wifi_bssid or "").strip().lower()
        matches = any(
            isinstance(item, dict)
            and str(item.get("ssid", "")).strip() == ssid
            and str(item.get("bssid", "")).strip().lower() == bssid
            for item in configured
        )
        if not configured:
            raise ProblemError(
                status=status.HTTP_403_FORBIDDEN,
                code="wifi_not_configured",
                title="Wi-Fi attendance is not configured",
                detail="The branch has no authorized Wi-Fi access point configured.",
            )
        if not matches:
            raise ProblemError(
                status=status.HTTP_403_FORBIDDEN,
                code="wifi_network_not_authorized",
                title="Wi-Fi network is not authorized",
                detail="Connect to the authorized branch Wi-Fi network before attendance.",
            )
        return 0
    distance = distance_metres(
        payload.latitude, payload.longitude, branch.latitude, branch.longitude
    )
    if location_required and distance > branch.geofence_radius_m:
        raise ProblemError(
            status=status.HTTP_403_FORBIDDEN,
            code="outside_branch_geofence",
            title="Outside branch range",
            detail=(
                f"The device is {distance}m from the branch; allowed range is "
                f"{branch.geofence_radius_m}m."
            ),
        )
    if payload.method == "qr":
        token = await session.scalar(
            select(BranchQrToken)
            .where(
                BranchQrToken.company_id == context.company_id,
                BranchQrToken.branch_id == branch.id,
                BranchQrToken.token_hash == qr_hash(payload.qr_token or ""),
                BranchQrToken.expires_at > now,
                BranchQrToken.revoked_at.is_(None),
            )
            .with_for_update()
        )
        if token is None:
            raise ProblemError(
                status=status.HTTP_403_FORBIDDEN,
                code="qr_token_invalid",
                title="QR code is invalid",
                detail="The QR code is expired or belongs to another branch.",
            )
        replay = await session.scalar(
            select(BranchQrTokenUse.id).where(
                BranchQrTokenUse.company_id == context.company_id,
                BranchQrTokenUse.token_id == token.id,
                BranchQrTokenUse.membership_id == context.membership.id,
                BranchQrTokenUse.action == action,
            )
        )
        if replay is not None:
            raise ProblemError(
                status=status.HTTP_409_CONFLICT,
                code="qr_token_replayed",
                title="QR code already used",
                detail="This QR code has already been used for this attendance action.",
            )
        session.add(
            BranchQrTokenUse(
                company_id=context.company_id,
                token_id=token.id,
                membership_id=context.membership.id,
                action=action,
            )
        )
    return distance


@router.post("/check-in", response_model=AttendanceRecordResponse, status_code=201)
async def check_in(
    payload: AttendanceActionRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    installation_id: InstallationId = None,
    idempotency_key: IdempotencyKey = None,
) -> AttendanceRecordResponse:
    context = tenant_context(auth_session)
    idempotency, replay = await begin_idempotency(
        session, context, "attendance.check_in", idempotency_key, payload
    )
    if replay is not None:
        return AttendanceRecordResponse.model_validate(replay)
    biometric_confirmed = accepted_biometric_declaration(context, payload)
    device = await approved_device(session, context, installation_id)
    now = datetime.now(UTC)
    branch, shift, work_date, scheduled_start, scheduled_end = await active_branch_and_shift(
        session, context, now
    )
    # A locationless (remote) shift is still one attendance session per
    # configured period.  Once that period ends, the employee must wait for
    # the next period/day instead of opening a new session against the same
    # window.  This prevents repeated remote check-ins after a checkout or
    # after the maintenance job closes a missing checkout.
    if remote_period_is_closed(shift, now, scheduled_end):
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="attendance_period_closed",
            title="Attendance period is closed",
            detail="This remote attendance period is closed. Wait for the next scheduled period.",
        )
    distance = await validate_location_and_qr(
        session,
        context,
        branch,
        payload,
        now,
        "check_in",
        location_required=payload.method != "wifi" and shift_requires_location(shift),
    )
    existing = await session.scalar(
        select(AttendanceRecord)
        .where(
            AttendanceRecord.company_id == context.company_id,
            AttendanceRecord.membership_id == context.membership.id,
            or_(
                AttendanceRecord.work_date == work_date,
                and_(
                    AttendanceRecord.checked_in_at.is_not(None),
                    AttendanceRecord.checked_out_at.is_(None),
                ),
            ),
        )
        .order_by(AttendanceRecord.checked_out_at.is_(None).desc())
        .with_for_update()
    )
    if existing is not None:
        # Maintenance can materialize an absent/on-leave row after a period
        # ends. Reuse that row when the employee records a late arrival for
        # the same period, rather than creating a duplicate attendance row.
        if (
            existing.checked_in_at is None
            and existing.scheduled_start_at == scheduled_start
            and existing.scheduled_end_at == scheduled_end
            and existing.status in {"absent", "on_leave"}
        ):
            late_minutes = max(
                0,
                int((now - scheduled_start).total_seconds() // 60)
                - shift.grace_period_minutes,
            )
            existing.checked_in_at = now
            existing.status = "late" if late_minutes else "on_time"
            existing.check_in_method = payload.method
            existing.late_minutes = late_minutes
            existing.review_status = "accepted"
            existing.version += 1
            session.add(
                AttendanceEvent(
                    company_id=context.company_id,
                    record_id=existing.id,
                    actor_membership_id=context.membership.id,
                    device_id=device.id,
                    event_type="check_in",
                    method=payload.method,
                    occurred_at=now,
                    latitude=payload.latitude,
                    longitude=payload.longitude,
                    distance_m=distance,
                    biometric_confirmed=biometric_confirmed,
                )
            )
            result = record_response(existing)
            complete_idempotency(idempotency, result, status.HTTP_200_OK)
            await session.commit()
            return result
        if existing.checked_out_at is not None:
            permission = await session.scalar(
                select(PermissionRequest)
                .where(
                    PermissionRequest.company_id == context.company_id,
                    PermissionRequest.membership_id == context.membership.id,
                    PermissionRequest.status == "approved",
                    PermissionRequest.starts_at <= now,
                    PermissionRequest.ends_at >= existing.checked_out_at,
                )
                .order_by(PermissionRequest.ends_at.desc())
                .with_for_update()
            )
            if permission is not None:
                planned_end = permission.ends_at
                return_late_minutes = max(0, int((now - planned_end).total_seconds() // 60))
                if now < permission.ends_at:
                    permission.ends_at = now
                existing.checked_out_at = None
                existing.check_out_method = None
                existing.worked_minutes = 0
                existing.early_departure_minutes = 0
                existing.status = (
                    "permission_return_late"
                    if return_late_minutes
                    else ("late" if existing.late_minutes else "on_time")
                )
                existing.version += 1
                session.add(
                    AttendanceEvent(
                        company_id=context.company_id,
                        record_id=existing.id,
                        actor_membership_id=context.membership.id,
                        device_id=device.id,
                        event_type="permission_return",
                        method=payload.method,
                        occurred_at=now,
                        latitude=payload.latitude,
                        longitude=payload.longitude,
                        distance_m=distance,
                        biometric_confirmed=biometric_confirmed,
                        details={
                            "permission_id": str(permission.id),
                            "planned_ends_at": planned_end.isoformat(),
                            "return_late_minutes": return_late_minutes,
                        },
                    )
                )
                result = record_response(existing)
                complete_idempotency(idempotency, result, status.HTTP_200_OK)
                await session.commit()
                return result
            if (
                not shift_requires_location(shift)
                and existing.scheduled_start_at == scheduled_start
                and existing.scheduled_end_at == scheduled_end
            ):
                raise ProblemError(
                    status=status.HTTP_409_CONFLICT,
                    code="attendance_period_closed",
                    title="Attendance period is closed",
                    detail=(
                        "This remote attendance period is already closed. "
                        "Wait for the next scheduled period."
                    ),
                )
        else:
            raise ProblemError(
                status=status.HTTP_409_CONFLICT,
                code="attendance_already_open",
                title="Attendance already recorded",
                detail="A duplicate check-in or a second open attendance session is not allowed.",
            )
        # A closed record from an earlier period (including an automatic
        # missing-checkout closure) must not block a later shift on the same
        # work date. The partial unique index still prevents two open sessions.
        existing = None
    late_minutes = max(
        0, int((now - scheduled_start).total_seconds() // 60) - shift.grace_period_minutes
    )
    record = AttendanceRecord(
        company_id=context.company_id,
        membership_id=context.membership.id,
        branch_id=branch.id,
        shift_id=shift.id,
        work_date=work_date,
        scheduled_start_at=scheduled_start,
        scheduled_end_at=scheduled_end,
        checked_in_at=now,
        status="late" if late_minutes else "on_time",
        check_in_method=payload.method,
        late_minutes=late_minutes,
    )
    session.add(record)
    await session.flush()
    session.add(
        AttendanceEvent(
            company_id=context.company_id,
            record_id=record.id,
            actor_membership_id=context.membership.id,
            device_id=device.id,
            event_type="check_in",
            method=payload.method,
            occurred_at=now,
            latitude=payload.latitude,
            longitude=payload.longitude,
            distance_m=distance,
            biometric_confirmed=biometric_confirmed,
        )
    )
    result = record_response(record)
    complete_idempotency(idempotency, result, status.HTTP_201_CREATED)
    await session.commit()
    return result


@router.post("/check-out", response_model=AttendanceRecordResponse)
async def check_out(
    payload: AttendanceActionRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    installation_id: InstallationId = None,
    idempotency_key: IdempotencyKey = None,
) -> AttendanceRecordResponse:
    context = tenant_context(auth_session)
    idempotency, replay = await begin_idempotency(
        session, context, "attendance.check_out", idempotency_key, payload
    )
    if replay is not None:
        return AttendanceRecordResponse.model_validate(replay)
    biometric_confirmed = accepted_biometric_declaration(context, payload)
    device = await approved_device(session, context, installation_id)
    now = datetime.now(UTC)
    record = await session.scalar(
        select(AttendanceRecord)
        .where(
            AttendanceRecord.company_id == context.company_id,
            AttendanceRecord.membership_id == context.membership.id,
            AttendanceRecord.checked_in_at.is_not(None),
            AttendanceRecord.checked_out_at.is_(None),
        )
        .with_for_update()
    )
    if record is None or record.checked_in_at is None:
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="attendance_not_open",
            title="No open attendance",
            detail="Check in before checking out.",
        )
    branch = await session.scalar(
        select(Branch).where(Branch.company_id == context.company_id, Branch.id == record.branch_id)
    )
    if branch is None:
        raise ProblemError(
            status=409,
            code="branch_missing",
            title="Branch missing",
            detail="The attendance branch no longer exists.",
        )
    shift = await session.scalar(
        select(Shift).where(Shift.company_id == context.company_id, Shift.id == record.shift_id)
    )
    if shift is None:
        raise ProblemError(
            status=409,
            code="shift_missing",
            title="Shift missing",
            detail="The attendance shift no longer exists.",
        )
    distance = await validate_location_and_qr(
        session,
        context,
        branch,
        payload,
        now,
        "check_out",
        location_required=payload.method != "wifi" and shift_requires_location(shift),
    )
    permission = await session.scalar(
        select(PermissionRequest.id).where(
            PermissionRequest.company_id == context.company_id,
            PermissionRequest.membership_id == context.membership.id,
            PermissionRequest.status == "approved",
            PermissionRequest.starts_at <= now,
            PermissionRequest.ends_at >= now,
        )
    )
    if now < record.scheduled_end_at and permission is None:
        remaining_minutes = max(
            1, int((record.scheduled_end_at - now).total_seconds() // 60)
        )
        raise ProblemError(
            status=status.HTTP_409_CONFLICT,
            code="checkout_too_early",
            title="Check-out is not available yet",
            detail=(
                "Check-out is available after the scheduled period ends, "
                f"in about {remaining_minutes} minute(s)."
            ),
        )
    early_minutes = max(0, int((record.scheduled_end_at - now).total_seconds() // 60))
    record.checked_out_at = now
    record.check_out_method = payload.method
    record.worked_minutes = max(0, int((now - record.checked_in_at).total_seconds() // 60))
    record.early_departure_minutes = early_minutes
    if early_minutes and permission is None:
        record.status = "early_departure_unauthorized"
    elif early_minutes:
        record.status = "on_permission"
    record.version += 1
    session.add(
        AttendanceEvent(
            company_id=context.company_id,
            record_id=record.id,
            actor_membership_id=context.membership.id,
            device_id=device.id,
            event_type="check_out",
            method=payload.method,
            occurred_at=now,
            latitude=payload.latitude,
            longitude=payload.longitude,
            distance_m=distance,
            biometric_confirmed=biometric_confirmed,
            details={"permission_id": str(permission) if permission else ""},
        )
    )
    result = record_response(record)
    complete_idempotency(idempotency, result, status.HTTP_200_OK)
    await session.commit()
    return result


@router.get("/me", response_model=list[AttendanceRecordResponse])
async def my_attendance(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[AttendanceRecordResponse]:
    context = tenant_context(auth_session)
    criteria = [
        AttendanceRecord.company_id == context.company_id,
        AttendanceRecord.membership_id == context.membership.id,
    ]
    if date_from:
        criteria.append(AttendanceRecord.work_date >= date_from)
    if date_to:
        criteria.append(AttendanceRecord.work_date <= date_to)
    records = await session.scalars(
        select(AttendanceRecord)
        .where(*criteria)
        .order_by(AttendanceRecord.work_date.desc())
        .limit(366)
    )
    return [record_response(item) for item in records]


@router.get(
    "/records/{record_id}/location-events",
    response_model=list[AttendanceLocationEventResponse],
)
async def attendance_location_events(
    record_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> list[AttendanceLocationEventResponse]:
    """Return the recorded GPS points with branch context for a map preview."""

    context = tenant_context(auth_session)
    record = await session.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.company_id == context.company_id,
            AttendanceRecord.id == record_id,
        )
    )
    if record is None:
        raise ProblemError(
            status=404,
            code="attendance_not_found",
            title="Attendance not found",
            detail="The attendance record does not exist in this company.",
        )
    if record.membership_id != context.membership.id:
        await require_permission(session, context, Permission.ATTENDANCE_VIEW)
        await require_membership_scope(session, context, record.membership_id)

    branch = await session.scalar(
        select(Branch).where(
            Branch.company_id == context.company_id,
            Branch.id == record.branch_id,
        )
    )
    if branch is None:
        raise ProblemError(
            status=404,
            code="branch_missing",
            title="Branch missing",
            detail="The branch linked to this attendance record no longer exists.",
        )

    employee_result = await session.execute(
        select(EmployeeProfile.display_name, User.full_name, User.email)
        .select_from(CompanyMembership)
        .join(
            User,
            User.id == CompanyMembership.user_id,
        )
        .outerjoin(
            EmployeeProfile,
            and_(
                EmployeeProfile.company_id == context.company_id,
                EmployeeProfile.membership_id == record.membership_id,
            ),
        )
        .where(
            CompanyMembership.company_id == context.company_id,
            CompanyMembership.id == record.membership_id,
        )
    )
    employee_name, full_name, employee_email = employee_result.first() or (
        None,
        None,
        None,
    )

    events = await session.scalars(
        select(AttendanceEvent)
        .where(
            AttendanceEvent.company_id == context.company_id,
            AttendanceEvent.record_id == record.id,
        )
        .order_by(AttendanceEvent.occurred_at.asc())
    )
    return [
        AttendanceLocationEventResponse(
            id=event.id,
            event_type=event.event_type,
            method=event.method,
            occurred_at=event.occurred_at,
            latitude=event.latitude,
            longitude=event.longitude,
            distance_m=event.distance_m,
            branch_name=branch.name,
            branch_latitude=branch.latitude,
            branch_longitude=branch.longitude,
            geofence_radius_m=branch.geofence_radius_m,
            employee_name=employee_name or full_name or employee_email,
        )
        for event in events
    ]


@router.get("", response_model=list[AttendanceRecordResponse])
async def list_attendance(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    membership_id: UUID | None = None,
    branch_id: UUID | None = None,
    record_status: Annotated[str | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[AttendanceRecordResponse]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ATTENDANCE_VIEW)
    criteria = [AttendanceRecord.company_id == context.company_id]
    visible = await visible_membership_ids(session, context)
    if visible is not None:
        criteria.append(AttendanceRecord.membership_id.in_(visible))
    if membership_id:
        await require_membership_scope(session, context, membership_id)
        criteria.append(AttendanceRecord.membership_id == membership_id)
    if branch_id:
        await require_branch_scope(session, context, branch_id)
        criteria.append(AttendanceRecord.branch_id == branch_id)
    if record_status:
        criteria.append(AttendanceRecord.status == record_status)
    if date_from:
        criteria.append(AttendanceRecord.work_date >= date_from)
    if date_to:
        criteria.append(AttendanceRecord.work_date <= date_to)
    rows = await session.execute(
        select(
            AttendanceRecord,
            CompanyMembership,
            User,
            EmployeeProfile,
            Branch,
            Shift,
        )
        .join(
            CompanyMembership,
            (CompanyMembership.company_id == AttendanceRecord.company_id)
            & (CompanyMembership.id == AttendanceRecord.membership_id),
        )
        .join(User, User.id == CompanyMembership.user_id)
        .outerjoin(
            EmployeeProfile,
            (EmployeeProfile.company_id == AttendanceRecord.company_id)
            & (EmployeeProfile.membership_id == AttendanceRecord.membership_id),
        )
        .join(
            Branch,
            (Branch.company_id == AttendanceRecord.company_id)
            & (Branch.id == AttendanceRecord.branch_id),
        )
        .join(
            Shift,
            (Shift.company_id == AttendanceRecord.company_id)
            & (Shift.id == AttendanceRecord.shift_id),
        )
        .where(*criteria)
        .order_by(AttendanceRecord.work_date.desc())
        .limit(2000)
    )
    return [
        manager_record_response(
            record,
            employee_name=profile.display_name if profile else user.full_name or user.email,
            employee_email=user.email,
            branch_name=branch.name,
            shift_name=shift.name,
        )
        for record, _membership, user, profile, branch, shift in rows.all()
    ]


@router.post("/reconcile")
async def reconcile_attendance(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    work_date: date | None = None,
) -> dict[str, int]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ATTENDANCE_MANAGE)
    await require_unrestricted_scope(session, context)
    target_date = work_date or (date.today() - timedelta(days=1))
    now = datetime.now(UTC)
    missing_count = 0
    absent_count = 0
    open_records = await session.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.company_id == context.company_id,
            AttendanceRecord.checked_in_at.is_not(None),
            AttendanceRecord.checked_out_at.is_(None),
            AttendanceRecord.scheduled_end_at < now - timedelta(hours=2),
        )
    )
    for record in open_records:
        record.status = "missing_check_out"
        record.review_status = "pending_review"
        record.version += 1
        missing_count += 1
    branch_assignments = list(
        await session.scalars(
            select(EmployeeBranchAssignment).where(
                EmployeeBranchAssignment.company_id == context.company_id,
                EmployeeBranchAssignment.effective_from <= target_date,
                or_(
                    EmployeeBranchAssignment.effective_to.is_(None),
                    EmployeeBranchAssignment.effective_to >= target_date,
                ),
            )
        )
    )
    for branch_assignment in branch_assignments:
        existing = await session.scalar(
            select(AttendanceRecord.id).where(
                AttendanceRecord.company_id == context.company_id,
                AttendanceRecord.membership_id == branch_assignment.membership_id,
                AttendanceRecord.work_date == target_date,
            )
        )
        if existing is not None:
            continue
        shift_assignment = await session.scalar(
            select(ShiftAssignment)
            .where(
                ShiftAssignment.company_id == context.company_id,
                or_(
                    ShiftAssignment.membership_id == branch_assignment.membership_id,
                    and_(
                        ShiftAssignment.membership_id.is_(None),
                        ShiftAssignment.branch_id == branch_assignment.branch_id,
                    ),
                ),
                ShiftAssignment.effective_from <= target_date,
                or_(
                    ShiftAssignment.effective_to.is_(None),
                    ShiftAssignment.effective_to >= target_date,
                ),
            )
            .order_by(ShiftAssignment.membership_id.is_not(None).desc())
        )
        if shift_assignment is None:
            continue
        shift = await session.scalar(
            select(Shift).where(
                Shift.company_id == context.company_id,
                Shift.id == shift_assignment.shift_id,
                Shift.is_active.is_(True),
            )
        )
        branch = await session.scalar(
            select(Branch).where(
                Branch.company_id == context.company_id,
                Branch.id == branch_assignment.branch_id,
            )
        )
        if shift is None or branch is None or target_date.weekday() not in shift.working_days:
            continue
        zone = ZoneInfo(branch.timezone)
        scheduled_start = datetime.combine(target_date, shift.start_time, zone).astimezone(UTC)
        end_date = target_date + timedelta(days=1) if shift.is_overnight else target_date
        scheduled_end = datetime.combine(end_date, shift.end_time, zone).astimezone(UTC)
        if scheduled_end >= now:
            continue
        leave = await session.scalar(
            select(LeaveRequest.id).where(
                LeaveRequest.company_id == context.company_id,
                LeaveRequest.membership_id == branch_assignment.membership_id,
                LeaveRequest.status == "approved",
                LeaveRequest.starts_on <= target_date,
                LeaveRequest.ends_on >= target_date,
            )
        )
        session.add(
            AttendanceRecord(
                company_id=context.company_id,
                membership_id=branch_assignment.membership_id,
                branch_id=branch.id,
                shift_id=shift.id,
                work_date=target_date,
                scheduled_start_at=scheduled_start,
                scheduled_end_at=scheduled_end,
                status="on_leave" if leave else "absent",
                review_status="accepted",
            )
        )
        absent_count += 1
    await session.commit()
    return {"missing_check_out": missing_count, "generated_absence_records": absent_count}


async def validate_manual_targets(
    session: AsyncSession,
    context: TenantContext,
    membership_id: UUID,
    branch_id: UUID,
    shift_id: UUID,
) -> tuple[Branch, Shift]:
    member = await session.scalar(
        select(CompanyMembership.id).where(
            CompanyMembership.company_id == context.company_id,
            CompanyMembership.id == membership_id,
            CompanyMembership.status == "active",
        )
    )
    branch = await session.scalar(
        select(Branch).where(Branch.company_id == context.company_id, Branch.id == branch_id)
    )
    shift = await session.scalar(
        select(Shift).where(Shift.company_id == context.company_id, Shift.id == shift_id)
    )
    if member is None or branch is None or shift is None:
        raise ProblemError(
            status=404,
            code="attendance_target_not_found",
            title="Attendance target not found",
            detail="Employee, branch, or shift was not found in this company.",
        )
    return branch, shift


@router.post("/manual", response_model=AttendanceRecordResponse, status_code=201)
async def create_manual_attendance(
    payload: ManualAttendanceRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> AttendanceRecordResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ATTENDANCE_MANAGE)
    await require_membership_scope(session, context, payload.membership_id)
    await require_branch_scope(session, context, payload.branch_id)
    branch, shift = await validate_manual_targets(
        session, context, payload.membership_id, payload.branch_id, payload.shift_id
    )
    await require_owned_attachment(session, context, payload.attachment_file_id)
    zone = ZoneInfo(branch.timezone)
    start = datetime.combine(payload.work_date, shift.start_time, zone).astimezone(UTC)
    end_date = payload.work_date + timedelta(days=1) if shift.is_overnight else payload.work_date
    end = datetime.combine(end_date, shift.end_time, zone).astimezone(UTC)
    record = AttendanceRecord(
        company_id=context.company_id,
        membership_id=payload.membership_id,
        branch_id=branch.id,
        shift_id=shift.id,
        work_date=payload.work_date,
        scheduled_start_at=start,
        scheduled_end_at=end,
        checked_in_at=payload.checked_in_at,
        checked_out_at=payload.checked_out_at,
        status="manual_attendance",
        check_in_method="manual",
        check_out_method="manual" if payload.checked_out_at else None,
        worked_minutes=(
            max(0, int((payload.checked_out_at - payload.checked_in_at).total_seconds() // 60))
            if payload.checked_out_at
            else 0
        ),
        is_manual=True,
        review_status="accepted",
    )
    session.add(record)
    await session.flush()
    session.add_all(
        [
            AttendanceEvent(
                company_id=context.company_id,
                record_id=record.id,
                actor_membership_id=context.membership.id,
                event_type="manual_created",
                method="manual",
                occurred_at=datetime.now(UTC),
                reason=payload.reason,
                attachment_file_id=payload.attachment_file_id,
            ),
            AuditLog(
                company_id=context.company_id,
                actor_membership_id=context.membership.id,
                action="attendance.manual_created",
                target_type="attendance_record",
                target_id=record.id,
                details={"reason": payload.reason, "membership_id": str(payload.membership_id)},
            ),
        ]
    )
    await session.commit()
    await session.refresh(record)
    return record_response(record)


@router.patch("/records/{record_id}", response_model=AttendanceRecordResponse)
async def correct_attendance(
    record_id: UUID,
    payload: CorrectAttendanceRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> AttendanceRecordResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ATTENDANCE_MANAGE)
    record = await session.scalar(
        select(AttendanceRecord)
        .where(AttendanceRecord.company_id == context.company_id, AttendanceRecord.id == record_id)
        .with_for_update()
    )
    if record is None:
        raise ProblemError(
            status=404,
            code="attendance_not_found",
            title="Attendance not found",
            detail="The record does not exist in this company.",
        )
    await require_membership_scope(session, context, record.membership_id)
    await require_owned_attachment(session, context, payload.attachment_file_id)
    if record.version != payload.version:
        raise ProblemError(
            status=409,
            code="concurrency_conflict",
            title="Attendance changed",
            detail="Reload the record before saving again.",
        )
    before = {
        "checked_in_at": record.checked_in_at.isoformat() if record.checked_in_at else None,
        "checked_out_at": record.checked_out_at.isoformat() if record.checked_out_at else None,
        "status": record.status,
    }
    for name in ("checked_in_at", "checked_out_at", "status"):
        value = getattr(payload, name)
        if value is not None:
            setattr(record, name, value)
    if record.checked_in_at and record.checked_out_at:
        if record.checked_out_at <= record.checked_in_at:
            raise ProblemError(
                status=422,
                code="attendance_time_order",
                title="Invalid attendance times",
                detail="Check-out must be after check-in.",
            )
        record.worked_minutes = max(
            0, int((record.checked_out_at - record.checked_in_at).total_seconds() // 60)
        )
    record.is_manual = True
    record.version += 1
    after = {
        "checked_in_at": record.checked_in_at.isoformat() if record.checked_in_at else None,
        "checked_out_at": record.checked_out_at.isoformat() if record.checked_out_at else None,
        "status": record.status,
    }
    session.add_all(
        [
            AttendanceEvent(
                company_id=context.company_id,
                record_id=record.id,
                actor_membership_id=context.membership.id,
                event_type="manual_corrected",
                method="manual",
                occurred_at=datetime.now(UTC),
                reason=payload.reason,
                attachment_file_id=payload.attachment_file_id,
                details={
                    "before": before,
                    "after": after,
                },
            ),
            AuditLog(
                company_id=context.company_id,
                actor_membership_id=context.membership.id,
                action="attendance.corrected",
                target_type="attendance_record",
                target_id=record.id,
                details={"reason": payload.reason, "before": before, "after": after},
            ),
        ]
    )
    await session.commit()
    await session.refresh(record)
    return record_response(record)


@router.post("/qr-tokens", response_model=QrTokenResponse, status_code=201)
async def create_qr_token(
    payload: CreateQrRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> QrTokenResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ATTENDANCE_MANAGE)
    await require_branch_scope(session, context, payload.branch_id)
    branch = await session.scalar(
        select(Branch.id).where(
            Branch.company_id == context.company_id,
            Branch.id == payload.branch_id,
            Branch.is_active.is_(True),
        )
    )
    if branch is None:
        raise ProblemError(
            status=404,
            code="branch_not_found",
            title="Branch not found",
            detail="The active branch was not found in this company.",
        )
    raw_token = token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=payload.valid_for_seconds)
    item = BranchQrToken(
        company_id=context.company_id,
        branch_id=payload.branch_id,
        created_by_membership_id=context.membership.id,
        token_hash=qr_hash(raw_token),
        expires_at=expires_at,
    )
    session.add(item)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="attendance.qr_token_created",
            target_type="branch_qr_token",
            target_id=item.id,
            details={"branch_id": str(payload.branch_id), "expires_at": expires_at.isoformat()},
        )
    )
    await session.commit()
    return QrTokenResponse(
        id=item.id,
        token=raw_token,
        branch_id=payload.branch_id,
        expires_at=expires_at,
    )


@router.get("/qr-tokens", response_model=list[QrTokenSummaryResponse])
async def list_qr_tokens(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    branch_id: UUID | None = None,
    include_inactive: bool = False,
) -> list[QrTokenSummaryResponse]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ATTENDANCE_MANAGE)
    criteria = [BranchQrToken.company_id == context.company_id]
    if branch_id is not None:
        await require_branch_scope(session, context, branch_id)
        criteria.append(BranchQrToken.branch_id == branch_id)
    if not include_inactive:
        criteria.extend(
            [
                BranchQrToken.revoked_at.is_(None),
                BranchQrToken.expires_at > datetime.now(UTC),
            ]
        )
    items = await session.scalars(
        select(BranchQrToken).where(*criteria).order_by(BranchQrToken.created_at.desc()).limit(1000)
    )
    return [QrTokenSummaryResponse.model_validate(item, from_attributes=True) for item in items]


@router.post("/qr-tokens/rotate", response_model=QrTokenResponse, status_code=201)
async def rotate_qr_token(
    payload: CreateQrRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> QrTokenResponse:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ATTENDANCE_MANAGE)
    await require_branch_scope(session, context, payload.branch_id)
    branch = await session.scalar(
        select(Branch.id).where(
            Branch.company_id == context.company_id,
            Branch.id == payload.branch_id,
            Branch.is_active.is_(True),
        )
    )
    if branch is None:
        raise ProblemError(
            status=404,
            code="branch_not_found",
            title="Branch not found",
            detail="The active branch was not found in this company.",
        )
    now = datetime.now(UTC)
    active_items = await session.scalars(
        select(BranchQrToken)
        .where(
            BranchQrToken.company_id == context.company_id,
            BranchQrToken.branch_id == payload.branch_id,
            BranchQrToken.revoked_at.is_(None),
            BranchQrToken.expires_at > now,
        )
        .with_for_update()
    )
    for existing in active_items:
        existing.revoked_at = now
    raw_token = token_urlsafe(32)
    item = BranchQrToken(
        company_id=context.company_id,
        branch_id=payload.branch_id,
        created_by_membership_id=context.membership.id,
        token_hash=qr_hash(raw_token),
        expires_at=now + timedelta(seconds=payload.valid_for_seconds),
    )
    session.add(item)
    await session.flush()
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="attendance.qr_tokens_rotated",
            target_type="branch_qr_token",
            target_id=item.id,
            details={"branch_id": str(payload.branch_id)},
        )
    )
    await session.commit()
    return QrTokenResponse(
        id=item.id,
        token=raw_token,
        branch_id=item.branch_id,
        expires_at=item.expires_at,
    )


@router.delete("/qr-tokens/{token_id}", status_code=204)
async def revoke_qr_token(
    token_id: UUID,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> None:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.ATTENDANCE_MANAGE)
    item = await session.scalar(
        select(BranchQrToken)
        .where(
            BranchQrToken.company_id == context.company_id,
            BranchQrToken.id == token_id,
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="qr_token_not_found",
            title="QR token not found",
            detail="The QR token does not exist in this company.",
        )
    await require_branch_scope(session, context, item.branch_id)
    if item.revoked_at is None:
        item.revoked_at = datetime.now(UTC)
        session.add(
            AuditLog(
                company_id=context.company_id,
                actor_membership_id=context.membership.id,
                action="attendance.qr_token_revoked",
                target_type="branch_qr_token",
                target_id=item.id,
                details={"branch_id": str(item.branch_id)},
            )
        )
        await session.commit()


@permissions_router.post("", response_model=PermissionResponse, status_code=201)
async def create_permission_request(
    payload: PermissionCreateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> PermissionResponse:
    context = tenant_context(auth_session)
    await require_owned_attachment(session, context, payload.attachment_file_id)
    ends_at = payload.ends_at
    if payload.request_type == "until_shift_end":
        (
            _branch,
            _shift,
            _work_date,
            _scheduled_start,
            scheduled_end,
        ) = await active_branch_and_shift(session, context, payload.starts_at.astimezone(UTC))
        ends_at = scheduled_end
    if ends_at is None or ends_at <= payload.starts_at:
        raise ProblemError(
            status=422,
            code="permission_window_invalid",
            title="Invalid permission window",
            detail="Permission end time must be after the start time.",
        )
    item = PermissionRequest(
        company_id=context.company_id,
        membership_id=context.membership.id,
        request_type=payload.request_type,
        starts_at=payload.starts_at,
        ends_at=ends_at,
        reason=payload.reason,
        attachment_file_id=payload.attachment_file_id,
    )
    session.add(item)
    await session.flush()
    manager_ids = await session.scalars(
        select(CompanyMembership.id).where(
            CompanyMembership.company_id == context.company_id,
            CompanyMembership.status == "active",
            CompanyMembership.role_code.in_(("OWNER", "MANAGER", "HR_OFFICER", "SUPERVISOR")),
        )
    )
    actor_name = await membership_actor_name(
        session, context.company_id, context.membership.id
    )
    session.add_all(
        [
            Notification(
                company_id=context.company_id,
                membership_id=manager_id,
                kind="permission_requested",
                title="Permission request",
                body="An employee submitted a permission or early-departure request.",
                actor_name=actor_name,
                target_type="permission_request",
                target_id=item.id,
                urgent=True,
            )
            for manager_id in manager_ids
        ]
    )
    await session.commit()
    await session.refresh(item)
    return permission_response(item)


@permissions_router.get("", response_model=list[PermissionResponse])
async def list_permission_requests(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    request_status: Annotated[str | None, Query(alias="status")] = None,
    mine: bool = False,
) -> list[PermissionResponse]:
    context = tenant_context(auth_session)
    criteria = [PermissionRequest.company_id == context.company_id]
    if mine or context.membership.role_code == "EMPLOYEE":
        criteria.append(PermissionRequest.membership_id == context.membership.id)
    else:
        await require_permission(session, context, Permission.PERMISSIONS_VIEW)
        visible = await visible_membership_ids(session, context)
        if visible is not None:
            criteria.append(PermissionRequest.membership_id.in_(visible))
    if request_status:
        criteria.append(PermissionRequest.status == request_status)
    items = list(await session.scalars(
        select(PermissionRequest)
        .where(*criteria)
        .order_by(PermissionRequest.created_at.desc())
        .limit(1000)
    ))
    details = await permission_employee_details(
        session,
        context.company_id,
        {item.membership_id for item in items},
    )
    return [
        permission_response(
            item,
            employee_name=details.get(item.membership_id, (None, ""))[0],
            employee_email=details.get(item.membership_id, (None, ""))[1],
        )
        for item in items
    ]


@permissions_router.post("/{request_id}/review", response_model=PermissionResponse)
async def review_permission_request(
    request_id: UUID,
    payload: PermissionReviewRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey = None,
) -> PermissionResponse:
    context = tenant_context(auth_session)
    idempotency, replay = await begin_idempotency(
        session,
        context,
        f"permission.review:{request_id}",
        idempotency_key,
        payload,
    )
    if replay is not None:
        return PermissionResponse.model_validate(replay)
    await require_permission(session, context, Permission.PERMISSIONS_MANAGE)
    item = await session.scalar(
        select(PermissionRequest)
        .where(
            PermissionRequest.company_id == context.company_id,
            PermissionRequest.id == request_id,
            PermissionRequest.status == "pending",
        )
        .with_for_update()
    )
    if item is None:
        raise ProblemError(
            status=404,
            code="permission_request_not_found",
            title="Permission request not found",
            detail="A pending request was not found in this company.",
        )
    await require_membership_scope(session, context, item.membership_id)
    item.status = payload.decision
    item.review_comment = payload.comment
    item.reviewed_by_membership_id = context.membership.id
    item.reviewed_at = datetime.now(UTC)
    actor_name = await membership_actor_name(
        session, context.company_id, context.membership.id
    )
    session.add(
        Notification(
            company_id=context.company_id,
            membership_id=item.membership_id,
            kind=f"permission_{payload.decision}",
            title="Permission request reviewed",
            body=f"Your permission request was {payload.decision}.",
            actor_name=actor_name,
            target_type="permission_request",
            target_id=item.id,
        )
    )
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action=f"permission.{payload.decision}",
            target_type="permission_request",
            target_id=item.id,
            details={"comment": payload.comment or ""},
        )
    )
    result = permission_response(item)
    complete_idempotency(idempotency, result, status.HTTP_200_OK)
    await session.commit()
    return result


@presence_router.post("", response_model=list[PresenceResponse], status_code=201)
async def create_presence_request(
    payload: PresenceCreateRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
) -> list[PresenceResponse]:
    context = tenant_context(auth_session)
    await require_permission(session, context, Permission.PRESENCE_MANAGE)
    target_ids = set(payload.membership_ids)
    if payload.branch_id:
        await require_branch_scope(session, context, payload.branch_id)
        branch_members = await session.scalars(
            select(EmployeeBranchAssignment.membership_id).where(
                EmployeeBranchAssignment.company_id == context.company_id,
                EmployeeBranchAssignment.branch_id == payload.branch_id,
                EmployeeBranchAssignment.effective_to.is_(None),
            )
        )
        target_ids.update(branch_members)
    if payload.group_id:
        await require_group_scope(session, context, payload.group_id)
        group_members = await session.scalars(
            select(EmployeeGroupMembership.membership_id).where(
                EmployeeGroupMembership.company_id == context.company_id,
                EmployeeGroupMembership.group_id == payload.group_id,
            )
        )
        target_ids.update(group_members)
    valid_ids = set(
        await session.scalars(
            select(CompanyMembership.id).where(
                CompanyMembership.company_id == context.company_id,
                CompanyMembership.id.in_(target_ids),
                CompanyMembership.status == "active",
            )
        )
    )
    if not valid_ids or valid_ids != target_ids:
        raise ProblemError(
            status=404,
            code="presence_target_not_found",
            title="Presence target not found",
            detail="Every recipient must be an active member of this company.",
        )
    visible = await visible_membership_ids(session, context)
    if visible is not None and not target_ids.issubset(visible):
        raise ProblemError(
            status=404,
            code="presence_target_not_found",
            title="Presence target not found",
            detail="Every recipient must belong to the current access scope.",
        )
    request = PresenceRequest(
        company_id=context.company_id,
        created_by_membership_id=context.membership.id,
        branch_id=payload.branch_id,
        group_id=payload.group_id,
        message=payload.message,
        deadline_at=datetime.now(UTC) + timedelta(seconds=payload.deadline_seconds),
    )
    session.add(request)
    await session.flush()
    actor_name = await membership_actor_name(
        session, context.company_id, context.membership.id
    )
    recipients = [
        PresenceRecipient(
            company_id=context.company_id, presence_request_id=request.id, membership_id=member_id
        )
        for member_id in valid_ids
    ]
    session.add_all(
        recipients
        + [
            Notification(
                company_id=context.company_id,
                membership_id=member_id,
                kind="presence_requested",
                title="Urgent presence check",
                body=request.message,
                actor_name=actor_name,
                target_type="presence_request",
                target_id=request.id,
                urgent=True,
            )
            for member_id in valid_ids
        ]
    )
    await session.commit()
    return [
        PresenceResponse(
            id=item.id,
            request_id=request.id,
            membership_id=item.membership_id,
            message=request.message,
            deadline_at=request.deadline_at,
            status=item.status,
            responded_at=None,
            distance_m=None,
            note=None,
        )
        for item in recipients
    ]


@presence_router.get("", response_model=list[PresenceResponse])
async def list_presence_requests(
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    mine: bool = False,
) -> list[PresenceResponse]:
    context = tenant_context(auth_session)
    criteria = [PresenceRecipient.company_id == context.company_id]
    if mine or context.membership.role_code == "EMPLOYEE":
        criteria.append(PresenceRecipient.membership_id == context.membership.id)
    else:
        await require_permission(session, context, Permission.PRESENCE_MANAGE)
        visible = await visible_membership_ids(session, context)
        if visible is not None:
            criteria.append(PresenceRecipient.membership_id.in_(visible))
    rows = (
        await session.execute(
            select(PresenceRecipient, PresenceRequest)
            .join(
                PresenceRequest,
                and_(
                    PresenceRequest.company_id == PresenceRecipient.company_id,
                    PresenceRequest.id == PresenceRecipient.presence_request_id,
                ),
            )
            .where(*criteria)
            .order_by(PresenceRequest.created_at.desc())
            .limit(1000)
        )
    ).all()
    now = datetime.now(UTC)
    result: list[PresenceResponse] = []
    for recipient, request in rows:
        item_status = (
            "no_response"
            if recipient.status == "pending" and request.deadline_at < now
            else recipient.status
        )
        result.append(
            PresenceResponse(
                id=recipient.id,
                request_id=request.id,
                membership_id=recipient.membership_id,
                message=request.message,
                deadline_at=request.deadline_at,
                status=item_status,
                responded_at=recipient.responded_at,
                distance_m=recipient.distance_m,
                note=recipient.note,
            )
        )
    return result


@presence_router.post("/{request_id}/respond", response_model=PresenceResponse)
async def respond_to_presence_request(
    request_id: UUID,
    payload: PresenceRespondRequest,
    auth_session: CurrentAuthSession,
    session: DatabaseSession,
    installation_id: InstallationId = None,
) -> PresenceResponse:
    context = tenant_context(auth_session)
    device = await approved_device(session, context, installation_id)
    row = (
        await session.execute(
            select(PresenceRecipient, PresenceRequest)
            .join(
                PresenceRequest,
                and_(
                    PresenceRequest.company_id == PresenceRecipient.company_id,
                    PresenceRequest.id == PresenceRecipient.presence_request_id,
                ),
            )
            .where(
                PresenceRecipient.company_id == context.company_id,
                PresenceRecipient.membership_id == context.membership.id,
                PresenceRecipient.presence_request_id == request_id,
            )
            .with_for_update()
        )
    ).first()
    if row is None:
        raise ProblemError(
            status=404,
            code="presence_request_not_found",
            title="Presence request not found",
            detail="The request was not sent to this employee.",
        )
    recipient, request = row
    now = datetime.now(UTC)
    if request.deadline_at < now:
        raise ProblemError(
            status=409,
            code="presence_request_expired",
            title="Presence request expired",
            detail="The response deadline has passed.",
        )
    branch_id = request.branch_id
    if branch_id is None:
        branch_id = await session.scalar(
            select(EmployeeBranchAssignment.branch_id).where(
                EmployeeBranchAssignment.company_id == context.company_id,
                EmployeeBranchAssignment.membership_id == context.membership.id,
                EmployeeBranchAssignment.effective_to.is_(None),
            )
        )
    branch = (
        await session.scalar(
            select(Branch).where(Branch.company_id == context.company_id, Branch.id == branch_id)
        )
        if branch_id
        else None
    )
    distance = (
        distance_metres(payload.latitude, payload.longitude, branch.latitude, branch.longitude)
        if branch
        else None
    )
    recipient.status = (
        "verified"
        if branch and distance is not None and distance <= branch.geofence_radius_m
        else ("outside_branch" if branch else "pending_review")
    )
    recipient.responded_at = now
    recipient.device_id = device.id
    recipient.latitude = payload.latitude
    recipient.longitude = payload.longitude
    recipient.distance_m = distance
    recipient.note = payload.note
    session.add(
        AuditLog(
            company_id=context.company_id,
            actor_membership_id=context.membership.id,
            action="presence.responded",
            target_type="presence_request",
            target_id=request.id,
            details={"status": recipient.status, "distance_m": distance or 0},
        )
    )
    await session.commit()
    return PresenceResponse(
        id=recipient.id,
        request_id=request.id,
        membership_id=recipient.membership_id,
        message=request.message,
        deadline_at=request.deadline_at,
        status=recipient.status,
        responded_at=recipient.responded_at,
        distance_m=recipient.distance_m,
        note=recipient.note,
    )
