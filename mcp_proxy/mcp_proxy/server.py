from decimal import Decimal
import time
from typing import Annotated, Awaitable, Callable, TypeVar

from fastmcp import FastMCP
from observability import get_tracer, log_event, setup_telemetry
from pydantic import Field

from .client import BankingApiClient
from .config import Settings, load_settings

T = TypeVar("T")


def create_mcp(settings: Settings | None = None) -> FastMCP:
    resolved_settings = settings or load_settings()
    setup_telemetry("mcp-proxy")
    client = BankingApiClient(
        resolved_settings.banking_api_base_url,
        resolved_settings.request_timeout_seconds,
    )
    mcp = FastMCP("Banking MCP Proxy")
    tracer = get_tracer("mcp-proxy.tools")

    async def _run_tool(tool_name: str, handler: Callable[[], Awaitable[T]]) -> T:
        started_at = time.perf_counter()
        with tracer.start_as_current_span("mcp-proxy.tool") as span:
            span.set_attribute("tool.name", tool_name)
            try:
                result = await handler()
            except Exception:
                log_event(
                    "mcp-proxy.tools",
                    "tool_call_failed",
                    tool_name=tool_name,
                    duration_ms=(time.perf_counter() - started_at) * 1000,
                )
                raise

        log_event(
            "mcp-proxy.tools",
            "tool_call_completed",
            tool_name=tool_name,
            duration_ms=(time.perf_counter() - started_at) * 1000,
        )
        return result

    @mcp.tool
    async def get_customer_profile(customer_id: str) -> dict:
        """Return the banking profile for a customer."""
        return await _run_tool(
            "get_customer_profile",
            lambda: client.get_customer_profile(customer_id),
        )

    @mcp.tool
    async def get_balance(customer_id: str) -> dict:
        """Return the current account balance for a customer."""
        return await _run_tool("get_balance", lambda: client.get_balance(customer_id))

    @mcp.tool
    async def get_card_limit(customer_id: str) -> dict:
        """Return the current credit card limit for a customer."""
        return await _run_tool(
            "get_card_limit",
            lambda: client.get_card_limit(customer_id),
        )

    @mcp.tool
    async def update_card_limit(
        customer_id: str,
        requested_limit: Annotated[Decimal, Field(ge=0)],
    ) -> dict:
        """Set the credit card limit for a customer."""
        return await _run_tool(
            "update_card_limit",
            lambda: client.update_card_limit(customer_id, requested_limit),
        )

    @mcp.tool
    async def create_pix(
        request_id: str,
        customer_id: str,
        destination_key: str,
        amount: Annotated[Decimal, Field(gt=0)],
    ) -> dict:
        """Create a PIX transfer using request_id as operation reference."""
        return await _run_tool(
            "create_pix",
            lambda: client.create_pix(
                request_id,
                customer_id,
                destination_key,
                amount,
            ),
        )

    return mcp
