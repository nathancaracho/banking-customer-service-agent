from pathlib import Path
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from identity.config import load_settings


class IdentityConfigTestCase(unittest.TestCase):
    def test_requires_database_url_from_env(self) -> None:
        original_database_url = os.environ.pop("IDENTITY_DATABASE_URL", None)

        try:
            with self.assertRaisesRegex(RuntimeError, "IDENTITY_DATABASE_URL"):
                load_settings()
        finally:
            if original_database_url is not None:
                os.environ["IDENTITY_DATABASE_URL"] = original_database_url


if __name__ == "__main__":
    unittest.main()
