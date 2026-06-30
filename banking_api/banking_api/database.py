from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def create_session_factory(
    database_url: str,
    schema: str,
) -> tuple[Engine, sessionmaker]:
    if database_url.startswith("sqlite"):
        raise ValueError("SQLite is not supported for this project")

    engine = create_engine(database_url)

    @event.listens_for(engine, "checkout")
    def _set_search_path(
        dbapi_connection,
        _connection_record,
        _connection_proxy,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()

    return engine, sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
