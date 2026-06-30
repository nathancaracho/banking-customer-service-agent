import asyncio
from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from agents import models_db
from agents.database import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("AGENTS_DATABASE_URL", "").strip()
database_schema = os.getenv("AGENTS_DATABASE_SCHEMA", "agents").strip()

if not database_url:
    raise RuntimeError("Missing required environment variable: AGENTS_DATABASE_URL")

config.set_main_option("sqlalchemy.url", database_url)
config.set_main_option("agents_schema", database_schema or "agents")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=True,
        version_table_schema=database_schema or None,
    )

    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    if database_schema:
        connection.execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{database_schema}"')
        )
        connection.commit()

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_schemas=True,
        version_table_schema=database_schema or None,
    )

    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
