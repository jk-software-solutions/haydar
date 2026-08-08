from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.workforce import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    PushDeviceToken,
)


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
        "employee_document": f"/app/requests?document={target_id}",
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
                delivery.provider_message_id = provider.send(
                    PushMessage(
                        token=token.token,
                        title=notification.title,
                        body=notification.body,
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
