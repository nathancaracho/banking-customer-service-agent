import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from observability import ChatMetrics, get_tracer, instrument_fastapi, log_event, setup_telemetry
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from .auth import (
    AuthenticationError,
    CurrentUser,
    authenticate_demo_user,
    create_access_token,
    decode_access_token,
)
from .broker import RabbitBroker
from .config import Settings, load_settings
from .database import create_session_factory
from .knowledge.routes import create_knowledge_router
from .memory import MemoryCompressor
from .rate_limit import RateLimitMiddleware
from .repository import (
    create_chat,
    create_message,
    get_chat,
    get_chat_memory,
    list_chats,
)
from observability import get_audit_buffer
from .schemas import (
    ChatDetailResponse,
    ChatResponse,
    LoginRequest,
    LoginResponse,
    MessageCreate,
    UserFinancialSummaryResponse,
)


bearer_scheme = HTTPBearer(auto_error=False)
_tracer = get_tracer("backend.chat")
_chat_metrics = ChatMetrics()


async def _get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.session_factory() as session:
        yield session


def _get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    settings = request.app.state.settings

    try:
        return decode_access_token(
            credentials.credentials,
            settings.jwt_secret,
            settings.jwt_algorithm,
        )
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from error


def _require_manager_or_admin(current_user: CurrentUser) -> None:
    if "manager" not in current_user.roles and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def create_app(
    settings: Settings | None = None,
    broker: RabbitBroker | None = None,
) -> FastAPI:
    resolved_settings = settings or load_settings()
    engine, session_factory = create_session_factory(
        resolved_settings.database_url,
        resolved_settings.database_schema,
    )
    resolved_broker = broker or RabbitBroker(
        resolved_settings.rabbitmq_url,
        resolved_settings.request_queue,
        resolved_settings.reply_queue,
        resolved_settings.stream_timeout_seconds,
    )
    setup_telemetry("backend", sqlalchemy_engines=[engine])

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        await resolved_broker.start()
        yield
        await resolved_broker.close()
        await engine.dispose()

    app = FastAPI(title="Backend Service", lifespan=_lifespan)
    instrument_fastapi(app)
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.broker = resolved_broker
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.include_router(
        create_knowledge_router(
            resolved_settings,
            _get_current_user,
            _get_session,
        )
    )

    @app.get("/health")
    async def _health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/admin/audit")
    async def _audit_query(
        category: str | None = None,
        actor_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
        current_user: CurrentUser = Depends(_get_current_user),
    ) -> list[dict[str, str | None]]:
        if "admin" not in current_user.roles and "manager" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        buffer = get_audit_buffer()
        return buffer.query(
            category=category,
            actor_id=actor_id,
            action=action,
            limit=min(limit, 500),
        )

    @app.get(
        "/v1/admin/users/{user_id}/financial-summary",
        response_model=UserFinancialSummaryResponse,
    )
    async def _user_financial_summary(
        user_id: str,
        current_user: CurrentUser = Depends(_get_current_user),
    ) -> UserFinancialSummaryResponse:
        _require_manager_or_admin(current_user)

        async with httpx.AsyncClient(
            base_url=resolved_settings.banking_api_url,
            timeout=10,
        ) as client:
            profile_response, balance_response, limit_response = await asyncio.gather(
                client.get(f"/v1/customers/{user_id}/profile"),
                client.get(f"/v1/customers/{user_id}/balance"),
                client.get(f"/v1/customers/{user_id}/card-limit"),
            )

        for response in (profile_response, balance_response, limit_response):
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Customer not found")
            response.raise_for_status()

        profile = profile_response.json()
        balance = Decimal(str(balance_response.json()["balance"]))
        current_limit = Decimal(str(limit_response.json()["current_limit"]))
        max_eligible_limit = (current_limit * Decimal("1.5")).quantize(
            Decimal("0.01")
        )
        missing_to_max_eligible = (max_eligible_limit - current_limit).quantize(
            Decimal("0.01")
        )

        return UserFinancialSummaryResponse(
            user_id=user_id,
            display_name=str(profile["display_name"]),
            segment=str(profile["segment"]),
            credit_score=int(profile["credit_score"]),
            balance=f"{balance:.2f}",
            current_limit=f"{current_limit:.2f}",
            max_eligible_limit=f"{max_eligible_limit:.2f}",
            missing_to_max_eligible=f"{missing_to_max_eligible:.2f}",
            increase_instructions=(
                "O gerente pode solicitar um aumento pelo fluxo de atendimento "
                "e o admin pode acompanhar a trilha de auditoria."
            ),
        )

    @app.post("/v1/auth/login", response_model=LoginResponse)
    async def _login(payload: LoginRequest) -> LoginResponse:
        try:
            current_user = authenticate_demo_user(
                payload.username,
                payload.password,
                resolved_settings.demo_password,
            )
        except AuthenticationError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            ) from error

        return LoginResponse(
            access_token=create_access_token(
                current_user,
                resolved_settings.jwt_secret,
                resolved_settings.jwt_algorithm,
            ),
            user_id=current_user.user_id,
            roles=list(current_user.roles),
        )

    @app.post(
        "/v1/chats",
        response_model=ChatResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def _create_chat_route(
        current_user: CurrentUser = Depends(_get_current_user),
        session: AsyncSession = Depends(_get_session),
    ) -> ChatResponse:
        return ChatResponse.model_validate(
            await create_chat(session, current_user.user_id)
        )

    @app.get("/v1/chats", response_model=list[ChatResponse])
    async def _list_chats_route(
        current_user: CurrentUser = Depends(_get_current_user),
        session: AsyncSession = Depends(_get_session),
    ) -> list[ChatResponse]:
        chats = await list_chats(session, current_user.user_id)
        return [ChatResponse.model_validate(chat) for chat in chats]

    @app.get("/v1/chats/{chat_id}", response_model=ChatDetailResponse)
    async def _get_chat_route(
        chat_id: str,
        current_user: CurrentUser = Depends(_get_current_user),
        session: AsyncSession = Depends(_get_session),
    ) -> ChatDetailResponse:
        chat = await get_chat(session, chat_id, current_user.user_id)

        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        return ChatDetailResponse.model_validate(chat)

    @app.post("/v1/chats/{chat_id}/messages")
    async def _submit_message_route(
        chat_id: str,
        payload: MessageCreate,
        request: Request,
        current_user: CurrentUser = Depends(_get_current_user),
        session: AsyncSession = Depends(_get_session),
    ) -> StreamingResponse:
        chat = await get_chat(session, chat_id, current_user.user_id)

        if chat is None:
            raise HTTPException(status_code=404, detail="Chat not found")

        await create_message(
            session,
            chat,
            role="user",
            content=payload.content,
            status="submitted",
        )
        summary, recent_messages = await get_chat_memory(
            session,
            chat.id,
            resolved_settings.recent_messages_limit,
        )
        request_id = str(uuid4())
        agent_request = {
            "request_id": request_id,
            "chat_id": chat.id,
            "subject": {
                "user_id": current_user.user_id,
                "roles": list(current_user.roles),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "message": {"role": "user", "content": payload.content},
                "memory": {
                    "summary": summary.content if summary else None,
                    "recent_messages": [
                        {"role": message.role, "content": message.content}
                        for message in recent_messages
                    ],
                },
            },
        }

        async def _event_stream():
            chunks: list[str] = []
            pending_chunks: dict[int, dict] = {}
            next_sequence = 1
            completed = False
            final_status = "completed"

            _chat_metrics.start_request()
            log_event(
                "backend.chat",
                "chat_request_started",
                request_id=request_id,
                chat_id=chat.id,
                user_id=current_user.user_id,
            )

            with _tracer.start_as_current_span("backend.chat.stream") as span:
                span.set_attribute("chat.id", chat.id)
                span.set_attribute("request.id", request_id)
                span.set_attribute("user.id", current_user.user_id)

                try:
                    async for event in request.app.state.broker.stream(agent_request):
                        if await request.is_disconnected():
                            final_status = "disconnected"
                            break

                        if event.get("type") == "chunk":
                            sequence = int(event["sequence"])

                            if sequence < next_sequence:
                                continue

                            pending_chunks[sequence] = event

                            while next_sequence in pending_chunks:
                                chunk_event = pending_chunks.pop(next_sequence)
                                chunks.append(
                                    str(
                                        chunk_event.get("payload", {}).get(
                                            "content", ""
                                        )
                                    )
                                )
                                _chat_metrics.record_first_chunk()
                                yield f"data: {json.dumps(chunk_event)}\n\n"
                                next_sequence += 1

                            continue

                        if event.get("type") in (
                            "completed",
                            "confirmation_required",
                            "failed",
                        ):
                            completed = True
                            final_status = str(event.get("type"))
                            for sequence in sorted(pending_chunks):
                                chunk_event = pending_chunks[sequence]
                                chunks.append(
                                    str(
                                        chunk_event.get("payload", {}).get(
                                            "content", ""
                                        )
                                    )
                                )
                                yield f"data: {json.dumps(chunk_event)}\n\n"

                            if event.get("type") == "failed":
                                final_content = (
                                    "Ocorreu um erro no processamento da sua "
                                    "mensagem. Por favor, tente novamente."
                                )
                            else:
                                final_content = str(
                                    event.get("payload", {}).get("content")
                                    or "".join(chunks)
                                )

                            await create_message(
                                session,
                                chat,
                                role="assistant",
                                content=final_content,
                                status=event.get("type"),
                            )

                            yield f"data: {json.dumps(event)}\n\n"
                            break
                except asyncio.CancelledError:
                    final_status = "cancelled"
                finally:
                    _chat_metrics.finish(status=final_status)
                    log_event(
                        "backend.chat",
                        "chat_request_finished",
                        request_id=request_id,
                        chat_id=chat.id,
                        status=final_status,
                    )

                    if not completed and chunks:
                        try:

                            async def _save_partial() -> None:
                                async with request.app.state.session_factory() as s:
                                    partial_chat = await get_chat(
                                        s, chat_id, current_user.user_id
                                    )
                                    if partial_chat:
                                        await create_message(
                                            s,
                                            partial_chat,
                                            "assistant",
                                            "".join(chunks),
                                            "interrupted",
                                        )

                            asyncio.create_task(_save_partial())
                        except Exception:
                            pass

        async def _compress_memory_task() -> None:
            compressor = MemoryCompressor(resolved_settings)
            async with request.app.state.session_factory() as bg_session:
                bg_chat = await get_chat(bg_session, chat_id, current_user.user_id)
                if bg_chat:
                    await compressor.compress_if_needed(
                        bg_session,
                        bg_chat,
                        resolved_settings.recent_messages_limit,
                    )

        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
            background=BackgroundTask(_compress_memory_task),
        )

    return app
