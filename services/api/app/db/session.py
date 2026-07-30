import logging
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> AsyncEngine | None:
    database_url = get_settings().database_url
    if not database_url:
        return None
    return create_async_engine(database_url, pool_pre_ping=True, poolclass=NullPool)


async def check_database() -> bool:
    engine = get_engine()
    if engine is None:
        return False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database readiness check failed")
        return False


async def dispose_engine() -> None:
    engine = get_engine()
    if engine is not None:
        await engine.dispose()
