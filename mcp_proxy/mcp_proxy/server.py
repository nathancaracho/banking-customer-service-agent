from decimal import Decimal
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from .client import BankingApiClient
from .config import Settings, load_settings


def create_mcp(settings: Settings | None = None) -> FastMCP:
    resolved_settings = settings or load_settings()
    client = BankingApiClient(
        resolved_settings.banking_api_base_url,
        resolved_settings.request_timeout_seconds,
    )
    mcp = FastMCP("Banking MCP Proxy")

    @mcp.tool
    async def get_customer_profile(customer_id: str) -> dict:
        """Return the banking profile for a customer."""
        return await client.get_customer_profile(customer_id)

    @mcp.tool
    async def get_balance(customer_id: str) -> dict:
        """Return the current account balance for a customer."""
        return await client.get_balance(customer_id)

    @mcp.tool
    async def get_card_limit(customer_id: str) -> dict:
        """Return the current credit card limit for a customer."""
        return await client.get_card_limit(customer_id)

    @mcp.tool
    async def update_card_limit(
        customer_id: str,
        requested_limit: Annotated[Decimal, Field(ge=0)],
    ) -> dict:
        """Set the credit card limit for a customer."""
        return await client.update_card_limit(customer_id, requested_limit)

    @mcp.tool
    async def create_pix(
        request_id: str,
        customer_id: str,
        destination_key: str,
        amount: Annotated[Decimal, Field(gt=0)],
    ) -> dict:
        """Create a PIX transfer using request_id as operation reference."""
        return await client.create_pix(
            request_id,
            customer_id,
            destination_key,
            amount,
        )

    return mcp
