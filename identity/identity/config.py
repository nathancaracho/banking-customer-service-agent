from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    database_schema: str | None


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    database_schema = os.getenv("IDENTITY_DATABASE_SCHEMA", "identity").strip()

    return Settings(
        database_url=_require_env("IDENTITY_DATABASE_URL"),
        database_schema=database_schema or None,
    )
