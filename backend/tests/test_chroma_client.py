import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.knowledge.chroma_client import (
    delete_chunks,
    update_chunks_active,
    upsert_chunks,
)


class ChromaClientTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_upserts_chunks_through_langchain_chroma(self) -> None:
        vector_store = MagicMock()
        vector_store.aadd_texts = AsyncMock()

        with patch(
            "backend.knowledge.chroma_client._get_vector_store",
            return_value=vector_store,
        ):
            await upsert_chunks(
                "http://chroma:8000",
                "banking_knowledge_base_v1",
                "http://litellm:4000",
                "sk-test",
                "kb-embedding",
                768,
                ["version:0"],
                ["policy"],
                [{"active": True}],
            )

        vector_store.aadd_texts.assert_awaited_once_with(
            texts=["policy"],
            metadatas=[{"active": True}],
            ids=["version:0"],
        )

    async def test_updates_metadata_and_deletes_by_id(self) -> None:
        collection = MagicMock()
        client = MagicMock()
        client.get_collection.return_value = collection
        vector_store = MagicMock()
        vector_store.adelete = AsyncMock()

        with (
            patch(
                "backend.knowledge.chroma_client._get_chroma_client",
                return_value=client,
            ),
            patch(
                "backend.knowledge.chroma_client.Chroma",
                return_value=vector_store,
            ),
        ):
            await update_chunks_active(
                "http://chroma:8000",
                "banking_knowledge_base_v1",
                ["version:0"],
                False,
            )
            await delete_chunks(
                "http://chroma:8000",
                "banking_knowledge_base_v1",
                ["version:0"],
            )

        collection.update.assert_called_once_with(
            ids=["version:0"],
            metadatas=[{"active": False}],
        )
        vector_store.adelete.assert_awaited_once_with(ids=["version:0"])
