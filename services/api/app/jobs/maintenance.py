import asyncio
import json
from datetime import UTC, date, datetime, time, timedelta
from typing import TypedDict
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import dispose_engine, get_sessionmaker
from app.models.attendance import AttendanceRecord, PresenceRecipient, PresenceRequest
from app.models.identity import CompanyMembership
from app.models.organization import (
    Branch,
    EmployeeBranchAssignment,
    EmployeeProfile,
    Shift,
    ShiftAssignment,
)
from app.models.platform import CompanySubscription
from app.models.workforce import (
    EmployeeDocument,
    LeaveRequest,
    Notification,
    TaskAssignee,
    WorkTask,
)
from app.services.notification_actor import membership_actor_name
from app.services.push_delivery import (
    deliver_pending_email_notifications,
    deliver_pending_notifications,
)


def _shift_periods(shift: Shift) -> list[tuple[time, time]]:
    """Return configured daily periods, falling back to the base shift."""
    recurrence = shift.recurrence if isinstance(shift.recurrence, dict) else {}
    raw_periods = recurrence.get("periods")
    periods: list[tuple[time, time]] = []
    if isinstance(raw_periods, list):
        for item in raw_periods:
            if not isinstance(item, dict):
                continue
            try:
                start = time.fromisoformat(str(item.get("start_time")))
                end = time.fromisoformat(str(item.get("end_time")))
            except (TypeError, ValueError):
                continue
            periods.append((start, end))
    return periods or [(shift.start_time, shift.end_time)]


def _period_window(work_date: date, start: time, end: time, zone: ZoneInfo) -> tuple[datetime, datetime]:
    local_start = datetime.combine(work_date, start, zone)
    end_date = work_date + timedelta(days=1) if end <= start else work_date
    return local_start, datetime.combine(end_date, end, zone)


def _checkout_grace_minutes(shift: Shift) -> int:
    """Return the post-shift window before an unclosed session is finalized."""
    recurrence = shift.recurrence if isinstance(shift.recurrence, dict) else {}
    configured = recurrence.get("checkout_grace_period_minutes")
    if configured is not None:
        try:
            return max(0, min(240, int(configured)))
        except (TypeError, ValueError):
            pass
    # Existing shifts predate the explicit field; preserve a safe 15-minute
    # default while still honoring a longer arrival grace when configured.
    return max(15, shift.grace_period_minutes)


class MaintenanceResult(TypedDict):
    missing_checkouts: int
    presence_timeouts: int
    task_reminders: int
    document_reminders: int
    expired_subscriptions: int
    push_created: int
    push_delivered: int
    push_failed: int
    push_blocked: int
    email_sent: int
    email_failed: int
    email_blocked: int
    attendance_reminders: int
    generated_absences: int


async def notification_exists(
    session: AsyncSession,
    *,
    company_id: UUID,
    membership_id: UUID,
    kind: str,
    target_id: UUID,
) -> bool:
    existing = await session.scalar(
        select(Notification.id).where(
            Notification.company_id == company_id,
            Notification.membership_id == membership_id,
            Notification.kind == kind,
            Notification.target_id == target_id,
        )
    )
    return existing is not None


async def expire_open_attendance(session: AsyncSession, now: datetime) -> int:
    records = list(
        await session.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.checked_in_at.is_not(None),
                AttendanceRecord.checked_out_at.is_(None),
                AttendanceRecord.scheduled_end_at <= now,
            )
        )
    )
    closed = 0
    for record in records:
        shift = await session.scalar(
            select(Shift).where(
                Shift.company_id == record.company_id,
                Shift.id == record.shift_id,
            )
        )
        grace_minutes = _checkout_grace_minutes(shift) if shift is not None else 30
        if now < record.scheduled_end_at + timedelta(minutes=grace_minutes):
            continue
        if record.checked_in_at is not None:
            record.checked_out_at = record.scheduled_end_at
            record.check_out_method = "system_timeout"
            record.worked_minutes = max(
                0, int((record.scheduled_end_at - record.checked_in_at).total_seconds() // 60)
            )
        record.early_departure_minutes = 0
        record.status = "missing_checkout"
        employee_name = await membership_actor_name(
            session, record.company_id, record.membership_id
        )
        if not await notification_exists(
            session,
            company_id=record.company_id,
            membership_id=record.membership_id,
            kind="missing_checkout",
            target_id=record.id,
        ):
            session.add(
                Notification(
                    company_id=record.company_id,
                    membership_id=record.membership_id,
                    kind="missing_checkout",
                    title="Missing check-out",
                    actor_name="System / النظام",
                    body=(
                        "Your shift was closed automatically after the "
                        f"{grace_minutes}-minute check-out grace period because no check-out was recorded."
                    ),
                    target_type="attendance_record",
                    target_id=record.id,
                )
            )
        closed += 1
        manager_ids = await session.scalars(
            select(CompanyMembership.id).where(
                CompanyMembership.company_id == record.company_id,
                CompanyMembership.status == "active",
                CompanyMembership.role_code.in_(("OWNER", "MANAGER", "HR_OFFICER")),
                CompanyMembership.id != record.membership_id,
            )
        )
        for manager_id in manager_ids:
            if await notification_exists(
                session,
                company_id=record.company_id,
                membership_id=manager_id,
                kind="missing_checkout",
                target_id=record.id,
            ):
                continue
            session.add(
                Notification(
                    company_id=record.company_id,
                    membership_id=manager_id,
                    kind="missing_checkout",
                    title="Missing employee check-out",
                    actor_name=employee_name,
                    body=(
                        "An employee shift was closed automatically after the "
                        f"{grace_minutes}-minute check-out grace period without a recorded check-out."
                    ),
                    target_type="attendance_record",
                    target_id=record.id,
                    urgent=True,
                )
            )
    return closed


async def create_attendance_reminders(session: AsyncSession, now: datetime) -> int:
    """Notify once per workday when an employee misses a check-in window.

    The maintenance timer is the source of truth for this reminder. A
    The reminder lists every period of a split shift in one notification.
    """
    assignments = list(
        await session.scalars(
            select(EmployeeBranchAssignment).where(
                EmployeeBranchAssignment.effective_from <= now.date(),
                (EmployeeBranchAssignment.effective_to.is_(None))
                | (EmployeeBranchAssignment.effective_to >= now.date()),
            )
        )
    )
    created = 0
    for branch_assignment in assignments:
        profile = await session.scalar(
            select(EmployeeProfile)
            .join(
                CompanyMembership,
                (CompanyMembership.company_id == EmployeeProfile.company_id)
                & (CompanyMembership.id == EmployeeProfile.membership_id),
            )
            .where(
                EmployeeProfile.company_id == branch_assignment.company_id,
                EmployeeProfile.membership_id == branch_assignment.membership_id,
                EmployeeProfile.attendance_enabled.is_(True),
                CompanyMembership.status == "active",
            )
        )
        branch = await session.scalar(
            select(Branch).where(
                Branch.company_id == branch_assignment.company_id,
                Branch.id == branch_assignment.branch_id,
                Branch.is_active.is_(True),
            )
        )
        if profile is None or branch is None:
            continue
        zone = ZoneInfo(branch.timezone)
        local_now = now.astimezone(zone)
        shift_assignment = await session.scalar(
            select(ShiftAssignment)
            .where(
                ShiftAssignment.company_id == branch_assignment.company_id,
                (
                    (ShiftAssignment.membership_id == branch_assignment.membership_id)
                    | (
                        ShiftAssignment.membership_id.is_(None)
                        & (ShiftAssignment.branch_id == branch_assignment.branch_id)
                    )
                ),
                ShiftAssignment.effective_from <= local_now.date(),
                (ShiftAssignment.effective_to.is_(None))
                | (ShiftAssignment.effective_to >= local_now.date()),
            )
            .order_by(ShiftAssignment.membership_id.is_not(None).desc())
        )
        if shift_assignment is None:
            continue
        shift = await session.scalar(
            select(Shift).where(
                Shift.company_id == branch_assignment.company_id,
                Shift.id == shift_assignment.shift_id,
                Shift.is_active.is_(True),
            )
        )
        if shift is None or local_now.date().weekday() not in shift.working_days:
            continue
        periods = _shift_periods(shift)
        schedule = "، ".join(
            f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
            for start, end in periods
        )
        for start_time, end_time in periods:
            local_start, local_end = _period_window(local_now.date(), start_time, end_time, zone)
            reminder_at = local_start + timedelta(minutes=shift.grace_period_minutes)
            if not (reminder_at <= local_now < reminder_at + timedelta(minutes=30)):
                continue
            scheduled_start = local_start.astimezone(UTC)
            if await session.scalar(
                select(AttendanceRecord.id).where(
                    AttendanceRecord.company_id == branch_assignment.company_id,
                    AttendanceRecord.membership_id == branch_assignment.membership_id,
                    AttendanceRecord.scheduled_start_at == scheduled_start,
                    AttendanceRecord.checked_in_at.is_not(None),
                )
            ) is not None:
                continue
            reminder_body = (
                f"وردياتك اليوم: {schedule}. "
                "لم يُسجَّل حضورك للفترة الحالية؛ سجّل حضورك أو قدّم طلب استئذان."
            )
            already_reminded = await session.scalar(
                select(Notification.id).where(
                    Notification.company_id == branch_assignment.company_id,
                    Notification.membership_id == branch_assignment.membership_id,
                    Notification.kind == "attendance_reminder",
                    Notification.target_type == "attendance_period",
                    Notification.created_at >= datetime.combine(
                        local_now.date(), time.min, zone
                    ).astimezone(UTC),
                )
            )
            if already_reminded is not None:
                continue
            session.add(
                Notification(
                    company_id=branch_assignment.company_id,
                    membership_id=branch_assignment.membership_id,
                    kind="attendance_reminder",
                    title="تذكير الحضور وجدول الورديات",
                    actor_name="System / النظام",
                    body=reminder_body,
                    target_type="attendance_period",
                    target_id=branch_assignment.membership_id,
                    urgent=True,
                )
            )
            created += 1
    return created


async def create_absence_records(session: AsyncSession, now: datetime) -> int:
    """Materialize a daily absent/on-leave row once each shift period ends."""
    assignments = list(
        await session.scalars(
            select(EmployeeBranchAssignment).where(
                EmployeeBranchAssignment.effective_from <= now.date(),
                (EmployeeBranchAssignment.effective_to.is_(None))
                | (EmployeeBranchAssignment.effective_to >= now.date()),
            )
        )
    )
    created = 0
    for branch_assignment in assignments:
        membership_active = await session.scalar(
            select(CompanyMembership.id).where(
                CompanyMembership.company_id == branch_assignment.company_id,
                CompanyMembership.id == branch_assignment.membership_id,
                CompanyMembership.status == "active",
            )
        )
        if membership_active is None:
            continue
        branch = await session.scalar(
            select(Branch).where(
                Branch.company_id == branch_assignment.company_id,
                Branch.id == branch_assignment.branch_id,
                Branch.is_active.is_(True),
            )
        )
        if branch is None:
            continue
        zone = ZoneInfo(branch.timezone)
        local_now = now.astimezone(zone)
        # Also inspect yesterday so overnight periods are closed after midnight.
        for work_date in {local_now.date(), local_now.date() - timedelta(days=1)}:
            shift_assignment = await session.scalar(
                select(ShiftAssignment)
                .where(
                    ShiftAssignment.company_id == branch_assignment.company_id,
                    (
                        (ShiftAssignment.membership_id == branch_assignment.membership_id)
                        | (
                            ShiftAssignment.membership_id.is_(None)
                            & (ShiftAssignment.branch_id == branch_assignment.branch_id)
                        )
                    ),
                    ShiftAssignment.effective_from <= work_date,
                    (ShiftAssignment.effective_to.is_(None))
                    | (ShiftAssignment.effective_to >= work_date),
                )
                .order_by(ShiftAssignment.membership_id.is_not(None).desc())
            )
            if shift_assignment is None:
                continue
            shift = await session.scalar(
                select(Shift).where(
                    Shift.company_id == branch_assignment.company_id,
                    Shift.id == shift_assignment.shift_id,
                    Shift.is_active.is_(True),
                )
            )
            if shift is None or work_date.weekday() not in shift.working_days:
                continue
            for start_time, end_time in _shift_periods(shift):
                local_start, local_end = _period_window(work_date, start_time, end_time, zone)
                if local_end.astimezone(UTC) > now:
                    continue
                scheduled_start = local_start.astimezone(UTC)
                scheduled_end = local_end.astimezone(UTC)
                exists = await session.scalar(
                    select(AttendanceRecord.id).where(
                        AttendanceRecord.company_id == branch_assignment.company_id,
                        AttendanceRecord.membership_id == branch_assignment.membership_id,
                        AttendanceRecord.scheduled_start_at == scheduled_start,
                        AttendanceRecord.scheduled_end_at == scheduled_end,
                    )
                )
                if exists is not None:
                    continue
                on_leave = await session.scalar(
                    select(LeaveRequest.id).where(
                        LeaveRequest.company_id == branch_assignment.company_id,
                        LeaveRequest.membership_id == branch_assignment.membership_id,
                        LeaveRequest.status == "approved",
                        LeaveRequest.starts_on <= work_date,
                        LeaveRequest.ends_on >= work_date,
                    )
                )
                record = AttendanceRecord(
                    company_id=branch_assignment.company_id,
                    membership_id=branch_assignment.membership_id,
                    branch_id=branch_assignment.branch_id,
                    shift_id=shift.id,
                    work_date=work_date,
                    scheduled_start_at=scheduled_start,
                    scheduled_end_at=scheduled_end,
                    status="on_leave" if on_leave else "absent",
                    review_status="accepted",
                )
                session.add(record)
                await session.flush()
                if not on_leave:
                    session.add(
                        Notification(
                            company_id=branch_assignment.company_id,
                            membership_id=branch_assignment.membership_id,
                            kind="attendance_absent",
                            title="Attendance marked absent",
                            actor_name="System / النظام",
                            body="The shift ended without a recorded check-in, so this day was marked absent.",
                            target_type="attendance_record",
                            target_id=record.id,
                            urgent=True,
                        )
                    )
                created += 1
    return created


async def expire_presence_requests(session: AsyncSession, now: datetime) -> int:
    recipients = list(
        await session.scalars(
            select(PresenceRecipient)
            .join(
                PresenceRequest,
                (PresenceRequest.company_id == PresenceRecipient.company_id)
                & (PresenceRequest.id == PresenceRecipient.presence_request_id),
            )
            .where(
                PresenceRecipient.status == "pending",
                PresenceRequest.deadline_at < now,
            )
        )
    )
    request_ids: set[UUID] = set()
    for recipient in recipients:
        recipient.status = "no_response"
        request_ids.add(recipient.presence_request_id)
    if request_ids:
        requests = await session.scalars(
            select(PresenceRequest).where(PresenceRequest.id.in_(request_ids))
        )
        for request in requests:
            request.status = "completed"
    return len(recipients)


async def create_task_reminders(session: AsyncSession, now: datetime) -> int:
    rows = list(
        (
            await session.execute(
                select(WorkTask, TaskAssignee)
                .join(
                    TaskAssignee,
                    (TaskAssignee.company_id == WorkTask.company_id)
                    & (TaskAssignee.task_id == WorkTask.id),
                )
                .where(
                    WorkTask.status.not_in(("completed",)),
                    WorkTask.due_at.is_not(None),
                    WorkTask.due_at >= now,
                    WorkTask.due_at <= now + timedelta(hours=24),
                )
            )
        ).all()
    )
    created = 0
    for task, assignee in rows:
        if await notification_exists(
            session,
            company_id=task.company_id,
            membership_id=assignee.membership_id,
            kind="task_due_soon",
            target_id=task.id,
        ):
            continue
        session.add(
            Notification(
                company_id=task.company_id,
                membership_id=assignee.membership_id,
                kind="task_due_soon",
                title=task.title,
                actor_name="System / النظام",
                body="This task is due within 24 hours.",
                target_type="work_task",
                target_id=task.id,
                urgent=task.priority == "urgent",
            )
        )
        created += 1
    return created


async def create_document_reminders(session: AsyncSession, today: date) -> int:
    documents = list(
        await session.scalars(
            select(EmployeeDocument).where(
                EmployeeDocument.expires_on.is_not(None),
                EmployeeDocument.expires_on <= today + timedelta(days=365),
            )
        )
    )
    created = 0
    for document in documents:
        if document.expires_on is None:
            continue
        days_remaining = (document.expires_on - today).days
        if days_remaining > document.reminder_days:
            continue
        kind = "document_expired" if days_remaining < 0 else "document_expiring"
        if await notification_exists(
            session,
            company_id=document.company_id,
            membership_id=document.membership_id,
            kind=kind,
            target_id=document.id,
        ):
            continue
        body = (
            "An employee document has expired."
            if days_remaining < 0
            else f"An employee document expires in {days_remaining} day(s)."
        )
        session.add(
            Notification(
                company_id=document.company_id,
                membership_id=document.membership_id,
                kind=kind,
                title="Employee document reminder",
                actor_name="System / النظام",
                body=body,
                target_type="employee_document",
                target_id=document.id,
                urgent=days_remaining <= 7,
            )
        )
        created += 1
    return created


async def expire_subscriptions(session: AsyncSession, now: datetime) -> int:
    subscriptions = list(
        await session.scalars(
            select(CompanySubscription).where(
                CompanySubscription.status.in_(("active", "trial")),
                CompanySubscription.ends_at <= now,
            )
        )
    )
    for subscription in subscriptions:
        subscription.status = "expired"
        subscription.updated_at = now
    return len(subscriptions)


async def run_maintenance(session: AsyncSession, now: datetime | None = None) -> MaintenanceResult:
    current = now or datetime.now(UTC)
    result: MaintenanceResult = {
        "missing_checkouts": await expire_open_attendance(session, current),
        "attendance_reminders": await create_attendance_reminders(session, current),
        "generated_absences": await create_absence_records(session, current),
        "presence_timeouts": await expire_presence_requests(session, current),
        "task_reminders": await create_task_reminders(session, current),
        "document_reminders": await create_document_reminders(session, current.date()),
        "expired_subscriptions": await expire_subscriptions(session, current),
        "push_created": 0,
        "push_delivered": 0,
        "push_failed": 0,
        "push_blocked": 0,
        "email_sent": 0,
        "email_failed": 0,
        "email_blocked": 0,
    }
    await session.commit()
    push = await deliver_pending_notifications(session)
    result["push_created"] = push["created"]
    result["push_delivered"] = push["delivered"]
    result["push_failed"] = push["failed"]
    result["push_blocked"] = push["blocked"]
    email = await deliver_pending_email_notifications(session)
    result["email_sent"] = email["sent"]
    result["email_failed"] = email["failed"]
    result["email_blocked"] = email["blocked"]
    return result


async def async_main() -> int:
    sessionmaker = get_sessionmaker()
    if sessionmaker is None:
        raise RuntimeError("DATABASE_URL is required to run maintenance")
    try:
        async with sessionmaker() as session:
            result = await run_maintenance(session)
        print(json.dumps(result, sort_keys=True))
        return 0
    finally:
        await dispose_engine()


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
