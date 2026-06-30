import os
import unittest

from backend.config import load_settings


class BackendConfigTestCase(unittest.TestCase):
    def tearDown(self) -> None:
        load_settings.cache_clear()
        os.environ.pop("BACKEND_JWT_SECRET", None)
        os.environ.pop("BACKEND_RABBITMQ_URL", None)
        os.environ.pop("BACKEND_FRONTEND_ORIGIN", None)
        os.environ.pop("BACKEND_DEMO_PASSWORD", None)

    def test_requires_database_url_from_env(self) -> None:
        original_database_url = os.environ.pop("BACKEND_DATABASE_URL", None)

        try:
            with self.assertRaisesRegex(RuntimeError, "BACKEND_DATABASE_URL"):
                load_settings()
        finally:
            if original_database_url is not None:
                os.environ["BACKEND_DATABASE_URL"] = original_database_url

    def test_caches_loaded_settings(self) -> None:
        original_database_url = os.environ.get("BACKEND_DATABASE_URL")
        os.environ["BACKEND_DATABASE_URL"] = (
            "postgresql+asyncpg://app:app@postgres:5432/app"
        )
        os.environ["BACKEND_JWT_SECRET"] = "test-secret"
        os.environ["BACKEND_RABBITMQ_URL"] = "amqp://app:app@rabbitmq:5672/app"
        os.environ["BACKEND_FRONTEND_ORIGIN"] = "http://localhost:5173"
        os.environ["BACKEND_DEMO_PASSWORD"] = "demo"

        try:
            first_settings = load_settings()
            os.environ["BACKEND_DATABASE_URL"] = (
                "postgresql+asyncpg://other:other@postgres:5432/other"
            )

            self.assertIs(load_settings(), first_settings)
        finally:
            if original_database_url is None:
                os.environ.pop("BACKEND_DATABASE_URL", None)
            else:
                os.environ["BACKEND_DATABASE_URL"] = original_database_url
