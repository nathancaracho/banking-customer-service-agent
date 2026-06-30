from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
import jwt

from backend.app import create_app
from backend.config import Settings
from backend.models import Chat


class FakeBroker:
    async def start(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def stream(self, request):
        yield {
            "request_id": request["request_id"],
            "chat_id": request["chat_id"],
            "type": "chunk",
            "sequence": 1,
            "payload": {"content": "Seu limite"},
        }
        yield {
            "request_id": request["request_id"],
            "chat_id": request["chat_id"],
            "type": "completed",
            "sequence": 2,
            "payload": {"content": "Seu limite é R$ 10.000"},
        }


class OutOfOrderBroker(FakeBroker):
    async def stream(self, request):
        yield {
            "request_id": request["request_id"],
            "chat_id": request["chat_id"],
            "type": "chunk",
            "sequence": 2,
            "payload": {"content": " segundo"},
        }
        yield {
            "request_id": request["request_id"],
            "chat_id": request["chat_id"],
            "type": "chunk",
            "sequence": 1,
            "payload": {"content": "primeiro"},
        }
        yield {
            "request_id": request["request_id"],
            "chat_id": request["chat_id"],
            "type": "completed",
            "sequence": 3,
            "payload": {},
        }


class BackendAppTestCase(unittest.TestCase):
    secret = "test-secret-with-at-least-32-bytes"

    def _create_client(self, broker=None) -> TestClient:
        settings = Settings(
            database_url="postgresql+asyncpg://app:app@postgres:5432/app",
            database_schema="backend",
            jwt_secret=self.secret,
            jwt_algorithm="HS256",
            rabbitmq_url="amqp://app:app@rabbitmq:5672/app",
            request_queue="agent.requests",
            reply_queue="agent.replies",
            stream_timeout_seconds=1,
            recent_messages_limit=20,
            frontend_origin="http://localhost:5173",
            demo_password="demo",
        )

        session = MagicMock()
        session_context = MagicMock()
        session_context.__aenter__.return_value = session
        session_context.__aexit__.return_value = False
        session_factory = MagicMock(return_value=session_context)

        with patch("backend.app.create_session_factory") as factory:
            factory.return_value = (MagicMock(), session_factory)
            return TestClient(create_app(settings, broker=broker or FakeBroker()))

    def _authorization_header(self) -> dict[str, str]:
        token = jwt.encode(
            {"sub": "usr_123", "roles": ["customer"]},
            self.secret,
            algorithm="HS256",
        )
        return {"Authorization": f"Bearer {token}"}

    def test_health_reports_service_is_ready(self) -> None:
        response = self._create_client().get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_rejects_chat_creation_without_access_token(self) -> None:
        response = self._create_client().post("/v1/chats")

        self.assertEqual(response.status_code, 401)

    def test_hides_chat_owned_by_another_user(self) -> None:
        with patch(
            "backend.app.get_chat",
            new=AsyncMock(return_value=None),
        ):
            response = self._create_client().get(
                "/v1/chats/chat_123",
                headers=self._authorization_header(),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Chat not found"})

    def test_streams_chunks_and_persists_completed_response(self) -> None:
        now = datetime.now(timezone.utc)
        chat = Chat(
            id="chat_123",
            user_id="usr_123",
            created_at=now,
            updated_at=now,
        )
        create_message_mock = AsyncMock()

        with (
            patch("backend.app.get_chat", new=AsyncMock(return_value=chat)),
            patch("backend.app.create_message", new=create_message_mock),
            patch(
                "backend.app.get_chat_memory",
                new=AsyncMock(return_value=(None, [])),
            ),
        ):
            response = self._create_client().post(
                "/v1/chats/chat_123/messages",
                headers=self._authorization_header(),
                json={"content": "Qual é o meu limite?"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "chunk"', response.text)
        self.assertIn('"type": "completed"', response.text)
        self.assertEqual(create_message_mock.await_count, 2)
        self.assertEqual(
            create_message_mock.await_args_list[1].kwargs["status"],
            "completed",
        )

    def test_orders_chunks_by_sequence(self) -> None:
        now = datetime.now(timezone.utc)
        chat = Chat(
            id="chat_123",
            user_id="usr_123",
            created_at=now,
            updated_at=now,
        )
        create_message_mock = AsyncMock()

        with (
            patch("backend.app.get_chat", new=AsyncMock(return_value=chat)),
            patch("backend.app.create_message", new=create_message_mock),
            patch(
                "backend.app.get_chat_memory",
                new=AsyncMock(return_value=(None, [])),
            ),
        ):
            response = self._create_client(OutOfOrderBroker()).post(
                "/v1/chats/chat_123/messages",
                headers=self._authorization_header(),
                json={"content": "Continue"},
            )

        self.assertLess(
            response.text.index('"sequence": 1'),
            response.text.index('"sequence": 2'),
        )
        self.assertEqual(
            create_message_mock.await_args_list[1].kwargs["content"],
            "primeiro segundo",
        )
