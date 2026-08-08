import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from typing import TypedDict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import dispose_engine, get_sessionmaker
from app.models.attendance import AttendanceRecord, PresenceRecipient, PresenceRequest
from app.models.platform import CompanySubscription
from app.models.workforce import EmployeeDocument, Notification, TaskAssignee, WorkTask


class MaintenanceResult(TypedDict):
    missing_checkouts: int
    presence_timeouts: int
    task_reminders: int
    document_reminders: int
    expired_subscriptions: int


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
                AttendanceRecord.scheduled_end_at < now - timedelta(hours=2),
            )
        )
    )
    for record in records:
        record.status = "missing_checkout"
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
                    body="Your attendance session needs manager review.",
                    target_type="attendance_record",
                    target_id=record.id,
                )
            )
    return len(records)


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
    result = MaintenanceResult(
        missing_checkouts=await expire_open_attendance(session, current),
        presence_timeouts=await expire_presence_requests(session, current),
        task_reminders=await create_task_reminders(session, current),
        document_reminders=await create_document_reminders(session, current.date()),
        expired_subscriptions=await expire_subscriptions(session, current),
    )
    await session.commit()
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
