import time
from functools import lru_cache
from urllib.parse import urlparse

import chromadb
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from observability import record_llm_call


class ChromaError(RuntimeError):
    pass


async def upsert_chunks(
    base_url: str,
    collection_name: str,
    litellm_url: str,
    litellm_api_key: str,
    embedding_model: str,
    embedding_dimensions: int,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    started_at = time.perf_counter()
    error_msg: str | None = None
    try:
        vector_store = _get_vector_store(
            base_url,
            collection_name,
            litellm_url,
            litellm_api_key,
            embedding_model,
            embedding_dimensions,
        )
        await vector_store.aadd_texts(
            texts=documents,
            metadatas=metadatas,
            ids=ids,
        )
    except Exception as exc:
        error_msg = str(exc)
        raise ChromaError("Chroma upsert failed") from exc
    finally:
        duration_ms = (time.perf_counter() - started_at) * 1000
        total_chars = sum(len(d) for d in documents)
        record_llm_call(
            model=embedding_model,
            operation="embedding",
            prompt=f"[batch ingestion] {len(documents)} chunks, {total_chars} chars",
            duration_ms=duration_ms,
            error=error_msg,
            extra_attributes={
                "batch.chunks": len(documents),
                "batch.total_chars": total_chars,
            },
        )


async def update_chunks_active(
    base_url: str,
    collection_name: str,
    ids: list[str],
    active: bool,
) -> None:
    if not ids:
        return

    try:
        collection = _get_chroma_client(base_url).get_collection(collection_name)
        collection.update(
            ids=ids,
            metadatas=[{"active": active} for _ in ids],
        )
    except Exception as error:
        raise ChromaError("Chroma metadata update failed") from error


async def delete_chunks(
    base_url: str,
    collection_name: str,
    ids: list[str],
) -> None:
    if not ids:
        return

    try:
        vector_store = Chroma(
            collection_name=collection_name,
            client=_get_chroma_client(base_url),
        )
        await vector_store.adelete(ids=ids)
    except Exception as error:
        raise ChromaError("Chroma delete failed") from error


@lru_cache(maxsize=8)
def _get_vector_store(
    base_url: str,
    collection_name: str,
    litellm_url: str,
    litellm_api_key: str,
    embedding_model: str,
    embedding_dimensions: int,
) -> Chroma:
    embeddings = OpenAIEmbeddings(
        model=embedding_model,
        base_url=f"{litellm_url}/v1",
        api_key=litellm_api_key,
        dimensions=embedding_dimensions,
        check_embedding_ctx_length=False,
        model_kwargs={"encoding_format": "float"},
    )
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        client=_get_chroma_client(base_url),
        collection_metadata={
            "embedding_dimensions": embedding_dimensions,
        },
    )


@lru_cache(maxsize=8)
def _get_chroma_client(base_url: str) -> chromadb.ClientAPI:
    parsed = urlparse(base_url)
    return chromadb.HttpClient(
        host=parsed.hostname or "localhost",
        port=parsed.port or (443 if parsed.scheme == "https" else 8000),
        ssl=parsed.scheme == "https",
    )
