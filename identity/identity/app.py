from collections.abc import Generator

from fastapi import Depends, FastAPI, Request
from sqlalchemy.orm import Session

from .config import Settings, load_settings
from .database import create_session_factory
from .repository import SqlAlchemyIdentityRepository
from .schemas import (
    AuthorizationRequest,
    AuthorizationResponse,
    AuthValidationRequest,
    AuthValidationResponse,
)
from .authorization import authorize_tool_call, validate_auth_context


def _get_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory

    with session_factory() as session:
        yield session


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    engine, session_factory = create_session_factory(
        resolved_settings.database_url,
        resolved_settings.database_schema,
    )

    app = FastAPI(title="Identity Service")
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    @app.post("/v1/auth/validate", response_model=AuthValidationResponse)
    def _validate_route(
        payload: AuthValidationRequest,
        session: Session = Depends(_get_session),
    ) -> AuthValidationResponse:
        repository = SqlAlchemyIdentityRepository(session)
        return validate_auth_context(repository, payload)

    @app.post("/v1/authorization/check", response_model=AuthorizationResponse)
    def _authorization_route(
        payload: AuthorizationRequest,
        session: Session = Depends(_get_session),
    ) -> AuthorizationResponse:
        repository = SqlAlchemyIdentityRepository(session)
        return authorize_tool_call(repository, payload)

    return app
