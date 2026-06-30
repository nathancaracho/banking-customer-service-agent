from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def create_session_factory(
    database_url: str,
    schema: str | None,
) -> tuple[Engine, sessionmaker]:
    if database_url.startswith("sqlite"):
        raise ValueError("SQLite is not supported for this project")

    engine_kwargs: dict[str, object] = {
        "future": True,
    }

    engine = create_engine(database_url, **engine_kwargs)

    if schema:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

        engine.dispose()

        @event.listens_for(engine, "connect")
        def _set_search_path(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute(f'SET search_path TO "{schema}"')
            cursor.close()

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    return engine, session_factory
