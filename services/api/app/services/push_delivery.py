from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Protocol

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.identity import CompanyMembership, User
from app.models.workforce import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    PushDeviceToken,
)
from app.services.email_delivery import send_notification_email


@dataclass(frozen=True)
class PushMessage:
    token: str
    title: str
    body: str
    data: dict[str, str]


class PushAdapter(Protocol):
    @property
    def configured(self) -> bool: ...

    def send(self, message: PushMessage) -> str: ...


class FirebasePushAdapter:
    @property
    def configured(self) -> bool:
        settings = get_settings()
        return bool(
            settings.firebase_project_id
            and settings.firebase_credentials_path
            and Path(settings.firebase_credentials_path).is_file()
        )

    def send(self, message: PushMessage) -> str:
        if not self.configured:
            raise RuntimeError("Firebase credentials are not configured")
        firebase_admin = import_module("firebase_admin")
        credentials = import_module("firebase_admin.credentials")
        messaging = import_module("firebase_admin.messaging")
        settings = get_settings()
        if not firebase_admin._apps:
            credential = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(credential, {"projectId": settings.firebase_project_id})
        firebase_message = messaging.Message(
            notification=messaging.Notification(title=message.title, body=message.body),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="hadir_notifications_v2",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default"),
                ),
            ),
            data=message.data,
            token=message.token,
        )
        return str(messaging.send(firebase_message))


def notification_deep_link(item: Notification) -> str:
    target_id = str(item.target_id) if item.target_id else ""
    routes = {
        "work_task": f"/app/tasks/{target_id}",
        "permission_request": f"/app/requests?permission={target_id}",
        "leave_request": f"/app/requests?leave={target_id}",
        "presence_request": f"/app/attendance?presence={target_id}",
        "geofence_exit_event": f"/app/attendance?geofence={target_id}",
        "attendance_record": f"/app/attendance?record={target_id}",
        "attendance_period": "/app/attendance",
        "employee_document": f"/app/requests?document={target_id}",
        "device_change_request": "/app/device-requests",
    }
    return routes.get(item.target_type or "", "/app")


async def deliver_pending_notifications(
    session: AsyncSession,
    adapter: PushAdapter | None = None,
    limit: int = 500,
) -> dict[str, int]:
    provider = adapter or FirebasePushAdapter()
    now = datetime.now(UTC)
    notifications = list(
        await session.scalars(
            select(Notification).order_by(Notification.created_at.asc()).limit(limit)
        )
    )
    created = delivered = failed = blocked = 0
    for notification in notifications:
        preference = await session.scalar(
            select(NotificationPreference).where(
                NotificationPreference.company_id == notification.company_id,
                NotificationPreference.membership_id == notification.membership_id,
            )
        )
        if preference is not None and (
            not preference.push_enabled or notification.kind in preference.muted_kinds
        ):
            continue
        tokens = list(
            await session.scalars(
                select(PushDeviceToken).where(
                    PushDeviceToken.company_id == notification.company_id,
                    PushDeviceToken.membership_id == notification.membership_id,
                    PushDeviceToken.is_active.is_(True),
                )
            )
        )
        for token in tokens:
            delivery = await session.scalar(
                select(NotificationDelivery).where(
                    NotificationDelivery.notification_id == notification.id,
                    NotificationDelivery.push_token_id == token.id,
                )
            )
            if delivery is None:
                delivery = NotificationDelivery(
                    company_id=notification.company_id,
                    membership_id=notification.membership_id,
                    notification_id=notification.id,
                    push_token_id=token.id,
                )
                session.add(delivery)
                await session.flush()
                created += 1
            if delivery.status == "delivered" or (
                delivery.next_attempt_at is not None and delivery.next_attempt_at > now
            ):
                continue
            if not provider.configured:
                delivery.status = "blocked_configuration"
                delivery.last_error = "Firebase credentials are not configured"
                blocked += 1
                continue
            try:
                delivery.attempts += 1
                push_body = notification.body
                if notification.actor_name:
                    push_body = f"{push_body}\nActor: {notification.actor_name}"
                delivery.provider_message_id = provider.send(
                    PushMessage(
                        token=token.token,
                        title=notification.title,
                        body=push_body,
                        data={
                            "notification_id": str(notification.id),
                            "kind": notification.kind,
                            "deep_link": notification_deep_link(notification),
                        },
                    )
                )
                delivery.status = "delivered"
                delivery.delivered_at = now
                delivery.last_error = None
                delivered += 1
            except Exception as exc:
                delivery.attempts += 1
                delivery.status = "retry"
                delivery.last_error = str(exc)[:1000]
                delivery.next_attempt_at = now + timedelta(
                    minutes=min(60, 2 ** min(delivery.attempts, 6))
                )
                failed += 1
    await session.commit()
    return {"created": created, "delivered": delivered, "failed": failed, "blocked": blocked}


async def deliver_pending_email_notifications(
    session: AsyncSession,
    limit: int = 200,
) -> dict[str, int]:
    """Send queued notification emails for members who opted in.

    A notification is marked as handled when email delivery is disabled or the
    notification kind is muted. Failed SMTP attempts remain queued for retry.
    """

    rows = (
        await session.execute(
            select(Notification, User.email, NotificationPreference)
            .join(
                CompanyMembership,
                and_(
                    CompanyMembership.company_id == Notification.company_id,
                    CompanyMembership.id == Notification.membership_id,
                ),
            )
            .join(User, User.id == CompanyMembership.user_id)
            .outerjoin(
                NotificationPreference,
                and_(
                    NotificationPreference.company_id == Notification.company_id,
                    NotificationPreference.membership_id == Notification.membership_id,
                ),
            )
            .where(Notification.email_sent_at.is_(None))
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
    ).all()
    sent = failed = blocked = 0
    for notification, recipient, preference in rows:
        if preference is None or not preference.email_enabled or notification.kind in preference.muted_kinds:
            notification.email_sent_at = datetime.now(UTC)
            blocked += 1
            continue
        delivered = await send_notification_email(
            recipient=recipient,
            title=notification.title,
            body=notification.body,
            actor_name=notification.actor_name,
        )
        if delivered:
            notification.email_sent_at = datetime.now(UTC)
            sent += 1
        else:
            failed += 1
    await session.commit()
    return {"sent": sent, "failed": failed, "blocked": blocked}
