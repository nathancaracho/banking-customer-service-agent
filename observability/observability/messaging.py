from __future__ import annotations

from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import propagate


def inject_headers(headers: dict[str, Any] | None = None) -> dict[str, Any]:
    carrier = dict(headers or {})
    propagate.inject(carrier)
    return carrier


def extract_context(headers: dict[str, Any] | None):
    return propagate.extract(headers or {})
