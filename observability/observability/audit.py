from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from opentelemetry import trace

from .audit_buffer import get_audit_buffer
from .logging import _LOGGER


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditCategory(str, Enum):
    AUTH = "auth"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    FINANCIAL = "financial"
    ADMIN = "admin"
    SECURITY = "security"


_SENSITIVE_KEYS = re.compile(
    r"(password|secret|token|api_key|authorization|cpf|credit_card|"
    r"card_number|cvv|pix_key|destination_key|source_key)",
    re.IGNORECASE,
)

_NUMERIC_MASK = re.compile(r"\b(\d{4})\d+(\d{4})\b")


def _mask_value(key: str, value: Any) -> Any:
    if isinstance(value, str) and _SENSITIVE_KEYS.search(key):
        if len(value) > 8:
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
        return "***"
    if isinstance(value, str) and _NUMERIC_MASK.search(value):
        return _NUMERIC_MASK.sub(r"\1***\2", value)
    return value


def _sanitize(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _mask_value(k, _sanitize(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize(item) for item in data]
    return data


def emit_audit_event(
    *,
    component: str,
    category: AuditCategory,
    action: str,
    severity: AuditSeverity = AuditSeverity.INFO,
    actor_id: str | None = None,
    target_id: str | None = None,
    decision: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
    chat_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "audit_category": category.value,
        "action": action,
        "severity": severity.value,
    }

    span_context = trace.get_current_span().get_span_context()

    if span_context.is_valid:
        payload["trace_id"] = format(span_context.trace_id, "032x")

    if actor_id is not None:
        payload["actor_id"] = actor_id
    if target_id is not None:
        payload["target_id"] = target_id
    if decision is not None:
        payload["decision"] = decision
    if reason is not None:
        payload["reason"] = reason
    if request_id is not None:
        payload["request_id"] = request_id
    if chat_id is not None:
        payload["chat_id"] = chat_id

    if metadata:
        payload["metadata"] = _sanitize(metadata)

    _LOGGER.info(json.dumps(payload, default=str))
    get_audit_buffer().append(payload)


def audit_auth_failure(
    component: str,
    *,
    actor_id: str | None = None,
    reason: str,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    emit_audit_event(
        component=component,
        category=AuditCategory.AUTH,
        action="auth.failure",
        severity=AuditSeverity.WARNING,
        actor_id=actor_id,
        reason=reason,
        request_id=request_id,
        metadata=metadata,
    )


def audit_authorization(
    component: str,
    *,
    actor_id: str,
    action: str,
    tool_name: str,
    decision: str,
    reason: str,
    request_id: str | None = None,
    chat_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    severity = (
        AuditSeverity.WARNING if decision == "deny" else AuditSeverity.INFO
    )
    emit_audit_event(
        component=component,
        category=AuditCategory.AUTHORIZATION,
        action=f"authorization.{action}",
        severity=severity,
        actor_id=actor_id,
        decision=decision,
        reason=reason,
        request_id=request_id,
        chat_id=chat_id,
        metadata={**(metadata or {}), "tool_name": tool_name},
    )


def audit_financial_operation(
    component: str,
    *,
    actor_id: str,
    operation: str,
    decision: str,
    request_id: str | None = None,
    chat_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    emit_audit_event(
        component=component,
        category=AuditCategory.FINANCIAL,
        action=f"financial.{operation}",
        severity=AuditSeverity.CRITICAL,
        actor_id=actor_id,
        decision=decision,
        request_id=request_id,
        chat_id=chat_id,
        metadata=metadata,
    )


def audit_admin_operation(
    component: str,
    *,
    actor_id: str,
    operation: str,
    target_id: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    emit_audit_event(
        component=component,
        category=AuditCategory.ADMIN,
        action=f"admin.{operation}",
        severity=AuditSeverity.CRITICAL,
        actor_id=actor_id,
        target_id=target_id,
        request_id=request_id,
        metadata=metadata,
    )


def audit_data_modification(
    component: str,
    *,
    actor_id: str,
    operation: str,
    target_id: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    emit_audit_event(
        component=component,
        category=AuditCategory.DATA_MODIFICATION,
        action=f"data.{operation}",
        severity=AuditSeverity.WARNING,
        actor_id=actor_id,
        target_id=target_id,
        request_id=request_id,
        metadata=metadata,
    )
