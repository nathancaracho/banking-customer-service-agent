from .bootstrap import get_meter, get_tracer, instrument_fastapi, setup_telemetry
from .llm import record_llm_call
from .logging import configure_logging, log_event
from .messaging import extract_context, inject_headers
from .metrics import ChatMetrics, ToolMetrics
from .audit import (
    AuditCategory,
    AuditSeverity,
    audit_admin_operation,
    audit_auth_failure,
    audit_authorization,
    audit_data_modification,
    audit_financial_operation,
    emit_audit_event,
)
from .audit_buffer import AuditLogBuffer, get_audit_buffer

__all__ = [
    "AuditCategory",
    "AuditLogBuffer",
    "AuditSeverity",
    "ChatMetrics",
    "ToolMetrics",
    "audit_admin_operation",
    "audit_auth_failure",
    "audit_authorization",
    "audit_data_modification",
    "audit_financial_operation",
    "configure_logging",
    "emit_audit_event",
    "extract_context",
    "get_audit_buffer",
    "get_meter",
    "get_tracer",
    "inject_headers",
    "instrument_fastapi",
    "log_event",
    "record_llm_call",
    "setup_telemetry",
]

def __getattr__(name: str):
    if name in __all__:
        module_map = {
            "AuditCategory": ".audit",
            "AuditLogBuffer": ".audit_buffer",
            "AuditSeverity": ".audit",
            "ChatMetrics": ".metrics",
            "ToolMetrics": ".metrics",
            "audit_admin_operation": ".audit",
            "audit_auth_failure": ".audit",
            "audit_authorization": ".audit",
            "audit_data_modification": ".audit",
            "audit_financial_operation": ".audit",
            "configure_logging": ".logging",
            "emit_audit_event": ".audit",
            "extract_context": ".messaging",
            "get_audit_buffer": ".audit_buffer",
            "get_meter": ".bootstrap",
            "get_tracer": ".bootstrap",
            "instrument_fastapi": ".bootstrap",
            "log_event": ".logging",
            "record_llm_call": ".llm",
            "setup_telemetry": ".bootstrap",
        }
        import importlib

        module = importlib.import_module(module_map[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
