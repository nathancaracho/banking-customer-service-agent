from collections.abc import Generator
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from observability import (
    audit_admin_operation,
    audit_authorization,
    instrument_fastapi,
    log_event,
    setup_telemetry,
)
from sqlalchemy.orm import Session

from .config import Settings, load_settings
from .database import create_session_factory
from .repository import SqlAlchemyIdentityRepository
from .schemas import (
    AdminUserResponse,
    AuthorizationRequest,
    AuthorizationResponse,
    AuthValidationRequest,
    AuthValidationResponse,
    UpdateRolesRequest,
    UserRoleResponse,
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
    setup_telemetry("identity", sqlalchemy_engines=[engine])

    app = FastAPI(title="Identity Service")
    instrument_fastapi(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.started_at = datetime.now(timezone.utc)

    @app.get("/health")
    def _health_route() -> dict[str, str]:
        return {"status": "ok"}

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
        try:
            repository = SqlAlchemyIdentityRepository(session)
            response = authorize_tool_call(repository, payload)
        except Exception as error:
            log_event(
                "identity.authorization",
                "authorization_error",
                request_id=payload.context.request_id,
                chat_id=payload.context.chat_id,
                tool_name=payload.context.tool_name,
                error=str(error),
            )
            audit_authorization(
                "identity",
                actor_id=payload.subject.user_id,
                action=payload.action,
                tool_name=payload.context.tool_name,
                decision="deny",
                reason=f"identity_unavailable: {type(error).__name__}",
                request_id=payload.context.request_id,
                chat_id=payload.context.chat_id,
                metadata={
                    "resource_type": payload.resource.type,
                    "owner_id": payload.resource.owner_id,
                    "error": str(error),
                },
            )
            return AuthorizationResponse(
                decision="deny",
                reason="Identity service is temporarily unavailable",
                policy_version="fail_closed",
                subject=payload.subject,
            )

        log_event(
            "identity.authorization",
            "authorization_decision",
            request_id=payload.context.request_id,
            chat_id=payload.context.chat_id,
            tool_name=payload.context.tool_name,
            decision=response.decision,
            reason=response.reason,
        )
        audit_authorization(
            "identity",
            actor_id=payload.subject.user_id,
            action=payload.action,
            tool_name=payload.context.tool_name,
            decision=response.decision,
            reason=response.reason,
            request_id=payload.context.request_id,
            chat_id=payload.context.chat_id,
            metadata={
                "resource_type": payload.resource.type,
                "owner_id": payload.resource.owner_id,
            },
        )
        return response

    @app.get("/v1/admin/users", response_model=list[AdminUserResponse])
    def _list_users_route(
        session: Session = Depends(_get_session),
    ) -> list[AdminUserResponse]:
        repository = SqlAlchemyIdentityRepository(session)
        users = repository.list_all_users()
        return [
            AdminUserResponse(
                id=user.id,
                display_name=user.display_name,
                is_active=user.is_active,
                created_at=user.created_at,
                roles=sorted(role.name for role in user.roles),
            )
            for user in users
        ]

    @app.get(
        "/v1/admin/users/{user_id}/roles",
        response_model=list[UserRoleResponse],
    )
    def _get_user_roles_route(
        user_id: str,
        session: Session = Depends(_get_session),
    ) -> list[UserRoleResponse]:
        repository = SqlAlchemyIdentityRepository(session)
        user = repository.get_user_with_roles(user_id)

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return [
            UserRoleResponse(name=role.name)
            for role in sorted(user.roles, key=lambda r: r.name)
        ]

    @app.put("/v1/admin/users/{user_id}/roles")
    def _update_user_roles_route(
        user_id: str,
        payload: UpdateRolesRequest,
        session: Session = Depends(_get_session),
    ) -> dict[str, str]:
        repository = SqlAlchemyIdentityRepository(session)
        user = repository.get_user_with_roles(user_id)

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        previous_roles = sorted(role.name for role in user.roles)
        repository.set_user_roles(user, payload.roles)
        audit_admin_operation(
            "identity",
            actor_id="admin",
            operation="update_user_roles",
            target_id=user_id,
            metadata={
                "previous_roles": previous_roles,
                "new_roles": sorted(payload.roles),
            },
        )
        return {"status": "ok"}

    return app
