import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import Settings
from app.db.base import Base
from app.models import Company, CompanyMembership, Invitation, RefreshSession, User

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_INCLUDED_MODELS = (Company, CompanyMembership, Invitation, RefreshSession, User)
target_metadata = Base.metadata


def get_migration_url() -> str:
    settings = Settings()
    migration_url = settings.migration_database_url
    if not migration_url:
        raise RuntimeError("MIGRATION_DATABASE_URL is required to run Alembic migrations")
    return str(migration_url)


def run_migrations_offline() -> None:
    context.configure(
        url=get_migration_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: object) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = get_migration_url()
    connectable = async_engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
