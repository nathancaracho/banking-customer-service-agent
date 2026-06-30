import os
import unittest

from mcp_proxy.config import load_settings


class McpConfigTestCase(unittest.TestCase):
    def tearDown(self) -> None:
        load_settings.cache_clear()

    def test_requires_banking_api_base_url(self) -> None:
        original_value = os.environ.pop("MCP_BANKING_API_BASE_URL", None)

        try:
            with self.assertRaisesRegex(RuntimeError, "MCP_BANKING_API_BASE_URL"):
                load_settings()
        finally:
            if original_value is not None:
                os.environ["MCP_BANKING_API_BASE_URL"] = original_value
