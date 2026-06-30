from __future__ import annotations

import os
from typing import Any

from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_CONFIGURED = False


def _is_enabled() -> bool:
    if os.getenv("OTEL_SDK_DISABLED", "").strip().lower() in {"1", "true", "yes"}:
        return False

    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def setup_telemetry(
    service_name: str,
    *,
    sqlalchemy_engines: list[Any] | None = None,
) -> None:
    global _CONFIGURED

    if _CONFIGURED or not _is_enabled():
        return

    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "deployment.environment": os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT", "local"),
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, insecure=True)
    )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True))
    )
    _logs.set_logger_provider(log_provider)

    import logging

    from opentelemetry.sdk._logs import LoggingHandler as OTELLoggingHandler

    logging.getLogger().addHandler(OTELLoggingHandler(level=logging.INFO, logger_provider=log_provider))

    LoggingInstrumentor().instrument(set_logging_format=True)
    HTTPXClientInstrumentor().instrument()

    for engine in sqlalchemy_engines or []:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine if hasattr(engine, "sync_engine") else engine
        )

    from .logging import configure_logging as _configure_logging

    _configure_logging()
    _CONFIGURED = True


def instrument_fastapi(app: Any) -> None:
    if not _is_enabled():
        return

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    return metrics.get_meter(name)
