from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.middleware import RateLimitMiddleware
from app.core.rbac_catalog import seed_builtin_rbac
from app.core.subscription_catalog import seed_builtin_plans
from app.db.base import Base
from app.db.session import get_session
from app.main import app


def reset_rate_limiter() -> None:
    middleware = app.middleware_stack
    while middleware is not None:
        if isinstance(middleware, RateLimitMiddleware):
            middleware.hits.clear()
        middleware = getattr(middleware, "app", None)


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    reset_rate_limiter()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
async def db_client() -> AsyncIterator[httpx.AsyncClient]:
    reset_rate_limiter()
    settings = get_settings()
    test_database_url = settings.test_database_url
    migration_database_url = settings.migration_database_url
    if not test_database_url or not migration_database_url:
        pytest.skip("TEST_DATABASE_URL and MIGRATION_DATABASE_URL are required")

    test_migration_url = migration_database_url.replace("/haydar_dev", "/haydar_test")
    migration_engine = create_async_engine(
        test_migration_url,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    app_engine = create_async_engine(test_database_url, pool_pre_ping=True, poolclass=NullPool)
    sessionmaker = async_sessionmaker(app_engine, expire_on_commit=False)

    async with migration_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    async with sessionmaker() as seed_session:
        await seed_builtin_rbac(seed_session)
        await seed_builtin_plans(seed_session)
        await seed_session.commit()

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)
        async with migration_engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await app_engine.dispose()
        await migration_engine.dispose()
