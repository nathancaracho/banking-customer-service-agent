from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    database_schema: str
    jwt_secret: str
    jwt_algorithm: str
    rabbitmq_url: str
    request_queue: str
    reply_queue: str
    stream_timeout_seconds: float
    recent_messages_limit: int
    frontend_origin: str
    demo_password: str


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings(
        database_url=_require_env("BACKEND_DATABASE_URL"),
        database_schema=os.getenv("BACKEND_DATABASE_SCHEMA", "backend").strip()
        or "backend",
        jwt_secret=_require_env("BACKEND_JWT_SECRET"),
        jwt_algorithm=os.getenv("BACKEND_JWT_ALGORITHM", "HS256").strip() or "HS256",
        rabbitmq_url=_require_env("BACKEND_RABBITMQ_URL"),
        request_queue=os.getenv("BACKEND_REQUEST_QUEUE", "agent.requests").strip()
        or "agent.requests",
        reply_queue=os.getenv("BACKEND_REPLY_QUEUE", "agent.replies").strip()
        or "agent.replies",
        stream_timeout_seconds=float(
            os.getenv("BACKEND_STREAM_TIMEOUT_SECONDS", "120")
        ),
        recent_messages_limit=int(os.getenv("BACKEND_RECENT_MESSAGES_LIMIT", "20")),
        frontend_origin=_require_env("BACKEND_FRONTEND_ORIGIN"),
        demo_password=_require_env("BACKEND_DEMO_PASSWORD"),
    )
