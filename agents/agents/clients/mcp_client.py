from decimal import Decimal
import re
import time
from typing import Any

from fastmcp import Client
from observability import ToolMetrics, get_tracer, log_event


_SENSITIVE_KEYS = re.compile(
    r"(password|secret|token|api_key|destination_key|source_key|pix_key)",
    re.IGNORECASE,
)


def _mask_arguments(args: dict[str, Any]) -> dict[str, Any]:
    masked = {}
    for key, value in args.items():
        if isinstance(value, str) and _SENSITIVE_KEYS.search(key):
            masked[key] = value[:2] + "***" if len(value) > 2 else "***"
        else:
            masked[key] = value
    return masked


class McpToolError(RuntimeError):
    pass


class McpToolClient:
    def __init__(self, mcp_url: str, timeout_seconds: float) -> None:
        self._mcp_url = mcp_url
        self._timeout_seconds = timeout_seconds
        self._tracer = get_tracer("agents.mcp")
        self._metrics = ToolMetrics()

    async def get_balance(self, customer_id: str) -> dict[str, Any]:
        return await self._call_tool(
            "get_balance",
            {
                "customer_id": customer_id,
            },
        )

    async def get_card_limit(self, customer_id: str) -> dict[str, Any]:
        return await self._call_tool(
            "get_card_limit",
            {
                "customer_id": customer_id,
            },
        )

    async def update_card_limit(
        self,
        customer_id: str,
        requested_limit: Decimal,
    ) -> dict[str, Any]:
        return await self._call_tool(
            "update_card_limit",
            {
                "customer_id": customer_id,
                "requested_limit": str(requested_limit),
            },
        )

    async def create_pix(
        self,
        request_id: str,
        customer_id: str,
        destination_key: str,
        amount: Decimal,
    ) -> dict[str, Any]:
        return await self._call_tool(
            "create_pix",
            {
                "request_id": request_id,
                "customer_id": customer_id,
                "destination_key": destination_key,
                "amount": str(amount),
            },
        )

    async def _call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        masked_args = _mask_arguments(arguments)

        log_event(
            "agents.mcp",
            "tool_call_started",
            tool_name=tool_name,
            arguments=masked_args,
        )

        with self._tracer.start_as_current_span("agents.mcp.tool_call") as span:
            span.set_attribute("tool.name", tool_name)
            try:
                async with Client(self._mcp_url, timeout=self._timeout_seconds) as client:
                    result = await client.call_tool(tool_name, arguments)
            except Exception as error:
                duration_ms = (time.perf_counter() - started_at) * 1000
                self._metrics.record_tool_call(
                    tool_name,
                    duration_ms,
                    success=False,
                )
                log_event(
                    "agents.mcp",
                    "tool_call_failed",
                    tool_name=tool_name,
                    duration_ms=round(duration_ms, 2),
                    error=str(error),
                )
                raise McpToolError(f"MCP tool call failed for {tool_name}") from error

        data = getattr(result, "data", None)

        if not isinstance(data, dict):
            duration_ms = (time.perf_counter() - started_at) * 1000
            self._metrics.record_tool_call(tool_name, duration_ms, success=False)
            raise McpToolError(f"MCP returned an invalid payload for {tool_name}")

        duration_ms = (time.perf_counter() - started_at) * 1000
        self._metrics.record_tool_call(tool_name, duration_ms, success=True)
        log_event(
            "agents.mcp",
            "tool_call_completed",
            tool_name=tool_name,
            duration_ms=round(duration_ms, 2),
        )
        return data
