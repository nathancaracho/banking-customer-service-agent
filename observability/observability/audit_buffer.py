from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any


class AuditLogBuffer:
    def __init__(self, max_size: int = 1000) -> None:
        self._buffer: deque[dict[str, Any]] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def append(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._buffer.append(event)

    def query(
        self,
        *,
        category: str | None = None,
        actor_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            results = list(self._buffer)

        if category:
            results = [e for e in results if e.get("audit_category") == category]
        if actor_id:
            results = [e for e in results if e.get("actor_id") == actor_id]
        if action:
            results = [e for e in results if e.get("action") == action]

        return results[-limit:]


_audit_buffer = AuditLogBuffer()


def get_audit_buffer() -> AuditLogBuffer:
    return _audit_buffer
