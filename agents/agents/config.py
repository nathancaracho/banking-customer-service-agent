from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    rabbitmq_url: str
    request_queue: str
    reply_queue: str
    identity_base_url: str
    identity_timeout_seconds: float
    mcp_url: str
    mcp_timeout_seconds: float
    litellm_url: str
    litellm_api_key: str
    litellm_model: str
    embedding_model: str
    embedding_dimensions: int
    chroma_url: str
    chroma_collection: str
    chroma_tenant: str
    chroma_database: str
    retrieval_results_limit: int
    response_chunk_size: int
    database_url: str
    database_schema: str


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings(
        rabbitmq_url=_require_env("AGENTS_RABBITMQ_URL"),
        request_queue=_require_env("AGENTS_REQUEST_QUEUE"),
        reply_queue=_require_env("AGENTS_REPLY_QUEUE"),
        identity_base_url=_require_env("AGENTS_IDENTITY_BASE_URL").rstrip("/"),
        identity_timeout_seconds=float(
            os.getenv("AGENTS_IDENTITY_TIMEOUT_SECONDS", "10")
        ),
        mcp_url=_require_env("AGENTS_MCP_URL").rstrip("/"),
        mcp_timeout_seconds=float(os.getenv("AGENTS_MCP_TIMEOUT_SECONDS", "20")),
        litellm_url=_require_env("AGENTS_LITELLM_URL").rstrip("/"),
        litellm_api_key=_require_env("LITELLM_MASTER_KEY"),
        litellm_model=os.getenv("AGENTS_LITELLM_MODEL", "chat-default"),
        embedding_model=_require_env("AGENTS_EMBEDDING_MODEL"),
        embedding_dimensions=int(_require_env("AGENTS_EMBEDDING_DIMENSIONS")),
        chroma_url=_require_env("AGENTS_CHROMA_URL").rstrip("/"),
        chroma_collection=_require_env("AGENTS_CHROMA_COLLECTION"),
        chroma_tenant=_require_env("AGENTS_CHROMA_TENANT"),
        chroma_database=_require_env("AGENTS_CHROMA_DATABASE"),
        retrieval_results_limit=int(os.getenv("AGENTS_RETRIEVAL_RESULTS_LIMIT", "3")),
        response_chunk_size=int(os.getenv("AGENTS_RESPONSE_CHUNK_SIZE", "140")),
        database_url=_require_env("AGENTS_DATABASE_URL"),
        database_schema=os.getenv("AGENTS_DATABASE_SCHEMA", "agents"),
    )
