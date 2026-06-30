import asyncio
from collections.abc import AsyncIterator
import json
from typing import Any

import aio_pika
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractRobustConnection,
)


class RabbitBroker:
    def __init__(
        self,
        url: str,
        request_queue: str,
        reply_queue: str,
        timeout_seconds: float,
    ) -> None:
        self._url = url
        self._request_queue_name = request_queue
        self._reply_queue_name = reply_queue
        self._timeout_seconds = timeout_seconds
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._request_queue: aio_pika.abc.AbstractQueue | None = None
        self._pending: dict[str, asyncio.Queue[dict[str, Any]]] = {}

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=100)
        self._request_queue = await self._channel.declare_queue(
            self._request_queue_name,
            durable=True,
        )
        reply_queue = await self._channel.declare_queue(
            self._reply_queue_name,
            durable=True,
        )
        await reply_queue.consume(self._consume_reply)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def stream(
        self,
        request: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        if self._channel is None or self._request_queue is None:
            raise RuntimeError("RabbitMQ broker is not started")

        request_id = str(request["request_id"])
        events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._pending[request_id] = events

        try:
            await self._channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(request).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    correlation_id=request_id,
                ),
                routing_key=self._request_queue.name,
            )

            while True:
                event = await asyncio.wait_for(
                    events.get(),
                    timeout=self._timeout_seconds,
                )
                yield event

                if event.get("type") in {"completed", "failed"}:
                    return
        except asyncio.TimeoutError:
            yield {
                "request_id": request_id,
                "chat_id": request["chat_id"],
                "type": "failed",
                "sequence": 1,
                "payload": {"code": "agent_timeout"},
            }
        finally:
            self._pending.pop(request_id, None)

    async def _consume_reply(self, message: AbstractIncomingMessage) -> None:
        async with message.process():
            event = json.loads(message.body)
            request_id = str(event.get("request_id", ""))
            pending = self._pending.get(request_id)

            if pending is not None:
                await pending.put(event)
