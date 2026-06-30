from __future__ import annotations

import time
from typing import Any

from opentelemetry import trace

from .logging import log_event
from .metrics import ToolMetrics


_MAX_PROMPT_LENGTH = 2000
_MAX_RESPONSE_LENGTH = 4000


def record_llm_call(
    *,
    model: str,
    operation: str = "chat",
    provider: str = "litellm",
    prompt: str | None = None,
    response: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    duration_ms: float,
    error: str | None = None,
    metrics: ToolMetrics | None = None,
    extra_attributes: dict[str, Any] | None = None,
) -> None:
    tracer = trace.get_tracer("gen_ai")
    attributes: dict[str, Any] = {
        "gen_ai.request.model": model,
        "gen_ai.operation.name": operation,
        "gen_ai.provider": provider,
    }

    if prompt_tokens is not None:
        attributes["gen_ai.usage.prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        attributes["gen_ai.usage.completion_tokens"] = completion_tokens
    if total_tokens is not None:
        attributes["gen_ai.usage.total_tokens"] = total_tokens
    if error is not None:
        attributes["error.type"] = error
        status = trace.Status(trace.StatusCode.ERROR, error)
    else:
        status = trace.Status(trace.StatusCode.OK)

    if extra_attributes:
        attributes.update(extra_attributes)

    with tracer.start_as_current_span(
        f"gen_ai.{operation}",
        attributes=attributes,
        record_exception=error is not None,
    ) as span:
        span.set_status(status)

        if prompt is not None:
            span.add_event(
                "gen_ai.prompt",
                {"content": prompt[: _MAX_PROMPT_LENGTH]},
            )
        if response is not None:
            span.add_event(
                "gen_ai.response",
                {"content": response[: _MAX_RESPONSE_LENGTH]},
            )

    if metrics is not None and operation == "chat":
        metrics.record_llm_usage(
            model=model,
            prompt_tokens=prompt_tokens or 0,
            completion_tokens=completion_tokens or 0,
        )

    log_event(
        "gen_ai",
        f"llm_{operation}",
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        duration_ms=round(duration_ms, 2),
        error=error,
    )
