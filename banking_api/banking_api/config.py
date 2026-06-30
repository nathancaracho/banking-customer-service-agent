from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
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
        database_url=_require_env("BANKING_API_DATABASE_URL"),
        database_schema=os.getenv(
            "BANKING_API_DATABASE_SCHEMA",
            "banking_api",
        ).strip()
        or "banking_api",
    )
