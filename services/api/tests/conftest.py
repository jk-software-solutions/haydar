from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
async def db_client() -> AsyncIterator[httpx.AsyncClient]:
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
