import logging
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_engine() -> AsyncEngine | None:
    database_url = get_settings().database_url
    if not database_url:
        return None
    return create_async_engine(database_url, pool_pre_ping=True, poolclass=NullPool)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession] | None:
    engine = get_engine()
    if engine is None:
        return None
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker()
    if sessionmaker is None:
        raise RuntimeError("DATABASE_URL is required to create database sessions")
    async with sessionmaker() as session:
        yield session


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
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
