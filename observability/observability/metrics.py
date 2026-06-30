from __future__ import annotations

import time
from dataclasses import dataclass, field

from opentelemetry import metrics


@dataclass
class ChatMetrics:
    component: str = "backend.chat"
    _request_counter: metrics.Counter | None = field(default=None, init=False, repr=False)
    _first_chunk_histogram: metrics.Histogram | None = field(default=None, init=False, repr=False)
    _response_duration_histogram: metrics.Histogram | None = field(default=None, init=False, repr=False)
    _started_at: float | None = field(default=None, init=False, repr=False)
    _first_chunk_recorded: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        meter = metrics.get_meter(self.component)
        self._request_counter = meter.create_counter(
            "chat_request_total",
            description="Total chat message requests handled by the backend",
        )
        self._first_chunk_histogram = meter.create_histogram(
            "chat_time_to_first_chunk_ms",
            unit="ms",
            description="Time until the first SSE chunk is emitted",
        )
        self._response_duration_histogram = meter.create_histogram(
            "chat_response_duration_ms",
            unit="ms",
            description="Total time to complete a chat response stream",
        )

    def start_request(self) -> None:
        self._started_at = time.perf_counter()
        self._first_chunk_recorded = False
        self._request_counter.add(1)

    def record_first_chunk(self) -> None:
        if self._started_at is None or self._first_chunk_recorded:
            return

        elapsed_ms = (time.perf_counter() - self._started_at) * 1000
        self._first_chunk_histogram.record(elapsed_ms)
        self._first_chunk_recorded = True

    def finish(self, *, status: str) -> None:
        if self._started_at is None:
            return

        elapsed_ms = (time.perf_counter() - self._started_at) * 1000
        self._response_duration_histogram.record(elapsed_ms, {"status": status})
        self._started_at = None


@dataclass
class ToolMetrics:
    component: str = "agents.tools"
    _tool_counter: metrics.Counter | None = field(default=None, init=False, repr=False)
    _tool_duration: metrics.Histogram | None = field(default=None, init=False, repr=False)
    _authorization_duration: metrics.Histogram | None = field(default=None, init=False, repr=False)
    _llm_tokens: metrics.Counter | None = field(default=None, init=False, repr=False)
    _llm_cost: metrics.Counter | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        meter = metrics.get_meter(self.component)
        self._tool_counter = meter.create_counter(
            "tool_call_total",
            description="Total MCP tool invocations",
        )
        self._tool_duration = meter.create_histogram(
            "tool_call_duration_ms",
            unit="ms",
            description="Duration of MCP tool invocations",
        )
        self._authorization_duration = meter.create_histogram(
            "authorization_duration_ms",
            unit="ms",
            description="Duration of identity authorization checks",
        )
        self._llm_tokens = meter.create_counter(
            "llm_token_usage_total",
            description="Total LLM tokens reported by the provider",
        )
        self._llm_cost = meter.create_counter(
            "llm_cost_total",
            description="Total LLM cost reported by the provider",
        )

    def record_tool_call(self, tool_name: str, duration_ms: float, *, success: bool) -> None:
        attributes = {"tool.name": tool_name, "success": success}
        self._tool_counter.add(1, attributes)
        self._tool_duration.record(duration_ms, attributes)

    def record_authorization(self, duration_ms: float, *, decision: str) -> None:
        self._authorization_duration.record(duration_ms, {"decision": decision})

    def record_llm_usage(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float | None = None,
    ) -> None:
        attributes = {"model": model}
        self._llm_tokens.add(prompt_tokens, {**attributes, "token.type": "prompt"})
        self._llm_tokens.add(completion_tokens, {**attributes, "token.type": "completion"})

        if cost is not None:
            self._llm_cost.add(cost, attributes)
