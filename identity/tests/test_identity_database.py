from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from identity.database import create_session_factory


class IdentityDatabaseTestCase(unittest.TestCase):
    def test_rejects_sqlite_database_urls(self) -> None:
        with self.assertRaisesRegex(ValueError, "SQLite is not supported"):
            create_session_factory(
                "sqlite+pysqlite:///:memory:",
                schema="identity",
            )


if __name__ == "__main__":
    unittest.main()
