from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_session_factory(
    database_url: str,
    schema: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    if database_url.startswith("sqlite"):
        raise ValueError("SQLite is not supported for this project")

    engine = create_async_engine(database_url)

    @event.listens_for(engine.sync_engine, "checkout")
    def _set_search_path(
        dbapi_connection,
        _connection_record,
        _connection_proxy,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()

    return engine, async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
