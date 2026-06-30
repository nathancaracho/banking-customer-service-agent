import time
from typing import Any
from urllib.parse import quote

import httpx
from langchain_openai import OpenAIEmbeddings
from observability import record_llm_call

from .config import Settings
from .models import KnowledgeHit


class KnowledgeBaseUnavailableError(RuntimeError):
    pass


def create_embeddings(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=f"{settings.litellm_url}/v1",
        api_key=settings.litellm_api_key,
        dimensions=settings.embedding_dimensions,
        check_embedding_ctx_length=False,
        model_kwargs={"encoding_format": "float"},
    )


class KnowledgeRetriever:
    def __init__(
        self,
        settings: Settings,
        embeddings: OpenAIEmbeddings | None = None,
    ) -> None:
        self._settings = settings
        self._embeddings = embeddings or create_embeddings(settings)
        self._model = settings.embedding_model

    async def retrieve(self, query: str) -> list[KnowledgeHit]:
        started_at = time.perf_counter()
        error_msg: str | None = None
        try:
            embedding = await self._embeddings.aembed_query(query)
            async with httpx.AsyncClient(
                base_url=self._settings.chroma_url,
                timeout=10,
            ) as client:
                collection_id = await _resolve_collection_id(client, self._settings)
                response = await client.post(
                    _build_query_path(
                        self._settings.chroma_tenant,
                        self._settings.chroma_database,
                        collection_id,
                    ),
                    json={
                        "query_embeddings": [embedding],
                        "n_results": self._settings.retrieval_results_limit,
                        "include": ["documents", "metadatas", "distances"],
                        "where": {"active": True},
                    },
                )
                response.raise_for_status()
        except Exception as exc:
            error_msg = str(exc)
            raise KnowledgeBaseUnavailableError(
                "Knowledge base is unavailable"
            ) from exc
        finally:
            duration_ms = (time.perf_counter() - started_at) * 1000
            record_llm_call(
                model=self._model,
                operation="embedding",
                prompt=query,
                duration_ms=duration_ms,
                error=error_msg,
            )

        payload = response.json()
        documents = _first_nested_list(payload.get("documents"))
        metadatas = _first_nested_list(payload.get("metadatas"))
        distances = _first_nested_list(payload.get("distances"))
        hits: list[KnowledgeHit] = []

        for index, document in enumerate(documents):
            if not document:
                continue

            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = distances[index] if index < len(distances) else None
            hits.append(
                KnowledgeHit(
                    document=str(document),
                    metadata=metadata or {},
                    distance=float(distance) if distance is not None else None,
                )
            )

        return hits


def _build_query_path(tenant: str, database: str, collection: str) -> str:
    return (
        "/api/v2/tenants/"
        f"{quote(tenant, safe='')}"
        "/databases/"
        f"{quote(database, safe='')}"
        "/collections/"
        f"{quote(collection, safe='')}"
        "/query"
    )


async def _resolve_collection_id(
    client: httpx.AsyncClient,
    settings: Settings,
) -> str:
    response = await client.get(
        "/api/v2/tenants/"
        f"{quote(settings.chroma_tenant, safe='')}"
        "/databases/"
        f"{quote(settings.chroma_database, safe='')}"
        "/collections/"
        f"{quote(settings.chroma_collection, safe='')}"
    )
    response.raise_for_status()
    payload = response.json()
    collection_id = payload.get("id")

    if not isinstance(collection_id, str) or not collection_id:
        raise KnowledgeBaseUnavailableError("Collection id not found")

    return collection_id


def _first_nested_list(value: Any) -> list[Any]:
    if isinstance(value, list) and value and isinstance(value[0], list):
        return list(value[0])

    return []
