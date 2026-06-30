from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    banking_api_base_url: str
    request_timeout_seconds: float
    host: str
    port: int


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings(
        banking_api_base_url=_require_env("MCP_BANKING_API_BASE_URL").rstrip("/"),
        request_timeout_seconds=float(
            os.getenv("MCP_REQUEST_TIMEOUT_SECONDS", "10")
        ),
        host=os.getenv("MCP_HOST", "0.0.0.0").strip() or "0.0.0.0",
        port=int(os.getenv("MCP_PORT", "8400")),
    )
