import asyncio
import time

import aio_pika
from observability import (
    audit_financial_operation,
    extract_context,
    get_meter,
    get_tracer,
    inject_headers,
    log_event,
)
from opentelemetry import context as otel_context
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .config import Settings
from .customer_service import AgentOutcome, CustomerServiceRunner
from .models import AgentEvent, AgentRequest
from .repository import (
    create_checkpoint,
    get_checkpoint_by_id,
    mark_checkpoint_completed,
    mark_checkpoint_failed,
)


class AgentWorker:
    def __init__(
        self,
        settings: Settings,
        agent: CustomerServiceRunner,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._settings = settings
        self._agent = agent
        self._session_factory = session_factory
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._reply_queue: AbstractQueue | None = None
        self._tracer = get_tracer("agents.worker")
        meter = get_meter("agents.worker")
        self._queue_depth_gauge = meter.create_gauge(
            "agents.queue.depth",
            description="Current depth of the request queue",
            unit="1",
        )
        self._processing_duration_histogram = meter.create_histogram(
            "agents.request.processing_duration_ms",
            description="Time to process an agent request",
            unit="ms",
        )

    async def serve_forever(self) -> None:
        self._connection = await aio_pika.connect_robust(self._settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=16)
        request_queue = await self._channel.declare_queue(
            self._settings.request_queue,
            durable=True,
        )
        self._reply_queue = await self._channel.declare_queue(
            self._settings.reply_queue,
            durable=True,
        )

        await request_queue.consume(self._consume_request)

        try:
            await asyncio.Future()
        finally:
            await self.close()

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def _consume_request(self, message: AbstractIncomingMessage) -> None:
        async with message.process():
            parent_context = extract_context(message.headers)
            token = otel_context.attach(parent_context)

            try:
                with self._tracer.start_as_current_span(
                    "agents.worker.process_request"
                ) as span:
                    request = AgentRequest.model_validate_json(message.body)
                    span.set_attribute("request.id", request.request_id)
                    span.set_attribute("chat.id", request.chat_id)
                    span.set_attribute("user.id", request.subject.user_id)
                    log_event(
                        "agents.worker",
                        "agent_request_consumed",
                        request_id=request.request_id,
                        chat_id=request.chat_id,
                    )
                    await self._handle_request(request)
            finally:
                otel_context.detach(token)

    async def _handle_request(self, request: AgentRequest) -> None:
        checkpoint_id = request.payload.checkpoint_id
        started_at = time.perf_counter()

        try:
            outcome = await self._agent(request)
            chunks = _chunk_response(
                outcome.content,
                self._settings.response_chunk_size,
            )

            for sequence, chunk in enumerate(chunks, start=1):
                await self._publish_event(
                    AgentEvent(
                        request_id=request.request_id,
                        chat_id=request.chat_id,
                        type="chunk",
                        sequence=sequence,
                        payload={"content": chunk},
                    )
                )

            if checkpoint_id is not None:
                async with self._session_factory() as session:
                    checkpoint = await get_checkpoint_by_id(session, checkpoint_id)
                    if checkpoint is not None:
                        await mark_checkpoint_completed(session, checkpoint)

            if outcome.requires_confirmation:
                async with self._session_factory() as session:
                    checkpoint = await create_checkpoint(
                        session,
                        request.request_id,
                        request.chat_id,
                        outcome.tool_name or "unknown",
                        outcome.parameters or {},
                        auth_decision=None,
                        subject={
                            "user_id": request.subject.user_id,
                            "roles": request.subject.roles,
                        },
                        confirmation_text=outcome.content,
                    )
                    new_checkpoint_id = checkpoint.id

                audit_financial_operation(
                    "agents",
                    actor_id=request.subject.user_id,
                    operation=f"{outcome.tool_name}.confirmation_required",
                    decision="pending",
                    request_id=request.request_id,
                    chat_id=request.chat_id,
                    metadata=outcome.parameters,
                )

                await self._publish_event(
                    AgentEvent(
                        request_id=request.request_id,
                        chat_id=request.chat_id,
                        type="confirmation_required",
                        sequence=len(chunks) + 1,
                        payload={
                            "content": outcome.content,
                            "checkpoint_id": new_checkpoint_id,
                        },
                    )
                )
            else:
                await self._publish_event(
                    AgentEvent(
                        request_id=request.request_id,
                        chat_id=request.chat_id,
                        type="completed",
                        sequence=len(chunks) + 1,
                        payload={"content": outcome.content},
                    )
                )
        except Exception:
            duration_ms = (time.perf_counter() - started_at) * 1000
            self._processing_duration_histogram.record(
                duration_ms,
                {"status": "error"},
            )
            await self._publish_event(
                AgentEvent(
                    request_id=request.request_id,
                    chat_id=request.chat_id,
                    type="failed",
                    sequence=1,
                    payload={"code": "agent_failed"},
                )
            )
        else:
            duration_ms = (time.perf_counter() - started_at) * 1000
            self._processing_duration_histogram.record(
                duration_ms,
                {"status": "success"},
            )

    async def _publish_event(self, event: AgentEvent) -> None:
        if self._channel is None or self._reply_queue is None:
            raise RuntimeError("Worker channel is not ready")

        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=event.model_dump_json().encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                correlation_id=event.request_id,
                headers=inject_headers(),
            ),
            routing_key=self._reply_queue.name,
        )
        log_event(
            "agents.worker",
            "reply_chunk_published",
            request_id=event.request_id,
            chat_id=event.chat_id,
            event_type=event.type,
            sequence=event.sequence,
        )


def _chunk_response(content: str, chunk_size: int) -> list[str]:
    text = content.strip()

    if not text:
        return [""]

    return [
        text[index : index + chunk_size]
        for index in range(0, len(text), chunk_size)
    ]
