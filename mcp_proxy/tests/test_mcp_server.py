from decimal import Decimal
import unittest
from unittest.mock import AsyncMock, patch

from fastmcp import Client

from mcp_proxy.config import Settings
from mcp_proxy.server import create_mcp


class McpServerTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_exposes_required_banking_tools(self) -> None:
        banking_client = AsyncMock()

        with patch(
            "mcp_proxy.server.BankingApiClient",
            return_value=banking_client,
        ):
            mcp = create_mcp(_settings())

        async with Client(mcp) as client:
            tools = await client.list_tools()

        self.assertEqual(
            {tool.name for tool in tools},
            {
                "get_customer_profile",
                "get_balance",
                "get_card_limit",
                "update_card_limit",
                "create_pix",
            },
        )

    async def test_forwards_card_limit_update_to_banking_api(self) -> None:
        banking_client = AsyncMock()
        banking_client.update_card_limit.return_value = {
            "customer_id": "usr_123",
            "current_limit": "15000.00",
        }

        with patch(
            "mcp_proxy.server.BankingApiClient",
            return_value=banking_client,
        ):
            mcp = create_mcp(_settings())

        async with Client(mcp) as client:
            result = await client.call_tool(
                "update_card_limit",
                {
                    "customer_id": "usr_123",
                    "requested_limit": "15000.00",
                },
            )

        self.assertEqual(result.data["current_limit"], "15000.00")
        banking_client.update_card_limit.assert_awaited_once_with(
            "usr_123",
            Decimal("15000.00"),
        )


def _settings() -> Settings:
    return Settings(
        banking_api_base_url="http://banking-api:8300",
        request_timeout_seconds=10,
        host="0.0.0.0",
        port=8400,
    )
