from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
from .repository import (
    create_chat,
    create_message,
    get_chat,
    get_chat_memory,
    list_chats,
)
from .schemas import (
    ChatDetailResponse,
    ChatResponse,
    LoginRequest,
    LoginResponse,
    MessageCreate,
)


bearer_scheme = HTTPBearer(auto_error=False)


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

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        await resolved_broker.start()
        yield
        await resolved_broker.close()
        await engine.dispose()

    app = FastAPI(title="Backend Service", lifespan=_lifespan)
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.broker = resolved_broker
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def _health() -> dict[str, str]:
        return {"status": "ok"}

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

            async for event in request.app.state.broker.stream(agent_request):
                if event.get("type") == "chunk":
                    sequence = int(event["sequence"])

                    if sequence < next_sequence:
                        continue

                    pending_chunks[sequence] = event

                    while next_sequence in pending_chunks:
                        chunk_event = pending_chunks.pop(next_sequence)
                        chunks.append(
                            str(chunk_event.get("payload", {}).get("content", ""))
                        )
                        yield f"data: {json.dumps(chunk_event)}\n\n"
                        next_sequence += 1

                    continue

                if event.get("type") == "completed":
                    for sequence in sorted(pending_chunks):
                        chunk_event = pending_chunks[sequence]
                        chunks.append(
                            str(chunk_event.get("payload", {}).get("content", ""))
                        )
                        yield f"data: {json.dumps(chunk_event)}\n\n"

                    final_content = str(
                        event.get("payload", {}).get("content") or "".join(chunks)
                    )
                    await create_message(
                        session,
                        chat,
                        role="assistant",
                        content=final_content,
                        status="completed",
                    )

                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    return app
