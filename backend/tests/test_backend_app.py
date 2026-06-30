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
            litellm_url="http://litellm:4000",
            litellm_api_key="sk-test",
            litellm_model="openai/gpt-4o-mini",
            embedding_model="kb-embedding",
            chroma_url="http://chroma:8000",
            chroma_collection="banking_knowledge_base_v1",
            kb_max_file_size_bytes=10_485_760,
            banking_api_url="http://banking-api:8300",
        )

        session = MagicMock()
        session_context = MagicMock()
        session_context.__aenter__.return_value = session
        session_context.__aexit__.return_value = False
        session_factory = MagicMock(return_value=session_context)

        with patch("backend.app.create_session_factory") as factory:
            factory.return_value = (MagicMock(), session_factory)
            return TestClient(create_app(settings, broker=broker or FakeBroker()))

    def _authorization_header(self, role: str = "customer") -> dict[str, str]:
        token = jwt.encode(
            {"sub": f"usr_{role}", "roles": [role]},
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

    def test_rejects_knowledge_upload_without_access_token(self) -> None:
        response = self._create_client().post(
            "/v1/knowledge/documents",
            files={"file": ("policy.txt", b"content", "text/plain")},
        )

        self.assertEqual(response.status_code, 401)

    def test_rejects_knowledge_upload_for_customer(self) -> None:
        response = self._create_client().post(
            "/v1/knowledge/documents",
            headers=self._authorization_header(),
            files={"file": ("policy.txt", b"content", "text/plain")},
        )

        self.assertEqual(response.status_code, 403)

    def test_rejects_unsupported_knowledge_file(self) -> None:
        response = self._create_client().post(
            "/v1/knowledge/documents",
            headers=self._authorization_header("admin"),
            files={"file": ("policy.csv", b"content", "text/csv")},
        )

        self.assertEqual(response.status_code, 415)

    def test_rejects_knowledge_reprocess_for_customer(self) -> None:
        with patch(
            "backend.knowledge.routes.get_document",
            new=AsyncMock(return_value=MagicMock()),
        ):
            response = self._create_client().post(
                "/v1/knowledge/documents/doc_123/reprocess",
                headers=self._authorization_header(),
                files={"file": ("policy.txt", b"content", "text/plain")},
            )

        self.assertEqual(response.status_code, 403)

    def test_reprocesses_knowledge_document_for_admin(self) -> None:
        version = MagicMock(
            id="version_2",
            status="completed",
            chunk_size=700,
            chunk_overlap=200,
            embedding_dimensions=768,
            chunk_count=4,
        )
        document = MagicMock(id="doc_123")

        with (
            patch(
                "backend.knowledge.routes.get_document",
                new=AsyncMock(return_value=document),
            ),
            patch(
                "backend.knowledge.routes.reprocess_document",
                new=AsyncMock(return_value=version),
            ),
        ):
            response = self._create_client().post(
                "/v1/knowledge/documents/doc_123/reprocess",
                headers=self._authorization_header("admin"),
                files={"file": ("policy.txt", b"content", "text/plain")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "ingestion_id": "version_2",
                "document_id": "doc_123",
                "status": "completed",
                "chunk_size": 700,
                "chunk_overlap": 200,
                "embedding_dimensions": 768,
                "chunk_count": 4,
            },
        )

    def test_rejects_knowledge_file_above_size_limit(self) -> None:
        response = self._create_client().post(
            "/v1/knowledge/documents",
            headers=self._authorization_header("admin"),
            files={
                "file": (
                    "policy.txt",
                    b"x" * 10_485_761,
                    "text/plain",
                )
            },
        )

        self.assertEqual(response.status_code, 413)

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

    def test_rejects_financial_summary_for_customer(self) -> None:
        response = self._create_client().get(
            "/v1/admin/users/usr_customer/financial-summary",
            headers=self._authorization_header(),
        )

        self.assertEqual(response.status_code, 403)

    def test_returns_financial_summary_for_manager(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            {
                "customer_id": "usr_customer",
                "display_name": "Joao Silva",
                "segment": "Personalite",
                "credit_score": 820,
            },
            {
                "customer_id": "usr_customer",
                "account_id": "acc-1",
                "balance": "2500.00",
            },
            {
                "customer_id": "usr_customer",
                "card_id": "card-1",
                "current_limit": "10000.00",
            },
        ]

        async_client = MagicMock()
        async_client.get = AsyncMock(side_effect=[mock_response, mock_response, mock_response])
        async_cm = MagicMock()
        async_cm.__aenter__ = AsyncMock(return_value=async_client)
        async_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.app.httpx.AsyncClient", return_value=async_cm):
            response = self._create_client().get(
                "/v1/admin/users/usr_customer/financial-summary",
                headers=self._authorization_header("manager"),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_limit"], "10000.00")
        self.assertEqual(response.json()["missing_to_max_eligible"], "5000.00")

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
