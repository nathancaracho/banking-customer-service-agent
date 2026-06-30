from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from banking_api.database import Base
from banking_api import models


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("BANKING_API_DATABASE_URL", "").strip()
database_schema = os.getenv("BANKING_API_DATABASE_SCHEMA", "banking_api").strip()

if not database_url:
    raise RuntimeError(
        "Missing required environment variable: BANKING_API_DATABASE_URL"
    )

config.set_main_option("sqlalchemy.url", database_url)
config.set_main_option("banking_api_schema", database_schema or "banking_api")

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


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
