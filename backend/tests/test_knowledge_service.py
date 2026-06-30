import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.config import Settings
from backend.knowledge.service import (
    KnowledgeIngestionError,
    ingest_document,
    reprocess_document,
)


class KnowledgeServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_marks_version_failed_when_embedding_fails(self) -> None:
        settings = Settings(
            database_url="postgresql+asyncpg://app:app@postgres:5432/app",
            database_schema="backend",
            jwt_secret="secret",
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
        document = MagicMock(id="doc_1", title="Policy")
        version = MagicMock(id="version_1")
        fail_version = AsyncMock()

        with (
            patch(
                "backend.knowledge.service.create_document",
                new=AsyncMock(return_value=(document, version)),
            ),
            patch(
                "backend.knowledge.service.upsert_chunks",
                new=AsyncMock(side_effect=RuntimeError("failed")),
            ),
            patch("backend.knowledge.service.fail_version", new=fail_version),
        ):
            with self.assertRaises(KnowledgeIngestionError):
                await ingest_document(
                    MagicMock(),
                    settings,
                    content=b"valid content",
                    file_name="policy.txt",
                    content_type="text/plain",
                    title="Policy",
                    source="manual_upload",
                    active=True,
                    created_by="usr_admin",
                )

        fail_version.assert_awaited_once()

    async def test_reprocess_deactivates_previous_chunks_before_upsert(self) -> None:
        settings = Settings(
            database_url="postgresql+asyncpg://app:app@postgres:5432/app",
            database_schema="backend",
            jwt_secret="secret",
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
        document = MagicMock(
            id="doc_1",
            title="Policy",
            source="manual_upload",
            is_active=True,
        )
        version = MagicMock(id="version_2")
        update_chunks_active = AsyncMock()
        upsert_chunks = AsyncMock()

        with (
            patch(
                "backend.knowledge.service.create_document_version",
                new=AsyncMock(return_value=version),
            ),
            patch(
                "backend.knowledge.service.get_chroma_ids",
                return_value=["version_1:0", "version_1:1"],
            ),
            patch(
                "backend.knowledge.service.update_chunks_active",
                new=update_chunks_active,
            ),
            patch(
                "backend.knowledge.service.upsert_chunks",
                new=upsert_chunks,
            ),
            patch("backend.knowledge.service.complete_version", new=AsyncMock()),
        ):
            await reprocess_document(
                session,
                settings,
                document,
                content=b"policy text",
                file_name="policy.txt",
                content_type="text/plain",
                title="Policy",
                source="manual_upload",
            )

        update_chunks_active.assert_awaited_once_with(
            "http://chroma:8000",
            "banking_knowledge_base_v1",
            ["version_1:0", "version_1:1"],
            False,
        )
        upsert_chunks.assert_awaited_once()
