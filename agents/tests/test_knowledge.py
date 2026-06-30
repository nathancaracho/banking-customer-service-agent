from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.config import Settings
from agents.knowledge import create_embeddings


class KnowledgeTestCase(unittest.TestCase):
    def test_create_embeddings_sets_expected_dimensions(self) -> None:
        settings = Settings(
            rabbitmq_url="amqp://guest:guest@rabbitmq:5672/app",
            request_queue="agent.requests",
            reply_queue="agent.replies",
            identity_base_url="http://identity:8100",
            identity_timeout_seconds=10,
            mcp_url="http://mcp-proxy:8400/mcp",
            mcp_timeout_seconds=20,
            litellm_url="http://litellm:4000",
            litellm_api_key="secret",
            litellm_model="chat-default",
            embedding_model="kb-embedding",
            embedding_dimensions=768,
            chroma_url="http://chroma:8000",
            chroma_collection="banking_knowledge_base_v1",
            chroma_tenant="default_tenant",
            chroma_database="default_database",
            retrieval_results_limit=3,
            response_chunk_size=140,
            database_url="postgresql+asyncpg://app:app@postgres:5432/app",
            database_schema="agents",
        )

        with patch("agents.knowledge.OpenAIEmbeddings") as mock_embeddings:
            create_embeddings(settings)

        mock_embeddings.assert_called_once_with(
            model="kb-embedding",
            base_url="http://litellm:4000/v1",
            api_key="secret",
            dimensions=768,
            check_embedding_ctx_length=False,
            model_kwargs={"encoding_format": "float"},
        )
