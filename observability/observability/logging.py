from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace

_LOGGER = logging.getLogger("banking.observability")


def configure_logging() -> None:
    if _LOGGER.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = True


def log_event(component: str, event: str, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "event": event,
        **fields,
    }
    span_context = trace.get_current_span().get_span_context()

    if span_context.is_valid:
        payload["trace_id"] = format(span_context.trace_id, "032x")

    _LOGGER.info(json.dumps(payload, default=str))
