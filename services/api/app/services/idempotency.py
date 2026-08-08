import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Annotated

from fastapi import Header
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import TenantContext
from app.core.errors import ProblemError
from app.models.idempotency import IdempotencyRecord

IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", min_length=8, max_length=200),
]


def request_digest(payload: BaseModel | dict[str, object]) -> str:
    value = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


async def begin_idempotency(
    session: AsyncSession,
    context: TenantContext,
    operation: str,
    key: str | None,
    payload: BaseModel | dict[str, object],
) -> tuple[IdempotencyRecord | None, dict[str, object] | None]:
    if key is None:
        return None, None
    digest = request_digest(payload)
    lock_name = f"{context.company_id}:{context.membership.id}:{operation}:{key}"
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(lock_name, 0))))
    existing = await session.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.company_id == context.company_id,
            IdempotencyRecord.membership_id == context.membership.id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.idempotency_key == key,
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    if existing is not None and existing.expires_at <= now:
        await session.delete(existing)
        await session.flush()
        existing = None
    if existing is not None:
        if existing.request_hash != digest:
            raise ProblemError(
                status=409,
                code="idempotency_key_conflict",
                title="Idempotency key conflict",
                detail="The same key was already used with a different request payload.",
            )
        if existing.response_body is None:
            raise ProblemError(
                status=409,
                code="idempotency_request_in_progress",
                title="Request is still in progress",
                detail="Retry this request shortly with the same key.",
            )
        return None, existing.response_body
    record = IdempotencyRecord(
        company_id=context.company_id,
        membership_id=context.membership.id,
        operation=operation,
        idempotency_key=key,
        request_hash=digest,
        expires_at=now + timedelta(hours=24),
    )
    session.add(record)
    await session.flush()
    return record, None


def complete_idempotency(
    record: IdempotencyRecord | None,
    response: BaseModel,
    status_code: int,
) -> None:
    if record is None:
        return
    record.status_code = status_code
    record.response_body = response.model_dump(mode="json")
