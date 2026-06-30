import unittest

from backend.database import create_session_factory


class BackendDatabaseTestCase(unittest.TestCase):
    def test_rejects_sqlite_database_urls(self) -> None:
        with self.assertRaisesRegex(ValueError, "SQLite is not supported"):
            create_session_factory(
                "sqlite+aiosqlite:///:memory:",
                schema="backend",
            )
