"""Production-Grade Distributed Tracing Module (OpenTelemetry).

Provides:
- TracerProvider initialization with OTLP gRPC exporter
- FastAPI and SQLAlchemy auto-instrumentation
- Kafka trace context injection/extraction helpers
- Utility to get current trace/span IDs for log enrichment
"""

import os
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = structlog.get_logger()

_propagator = TraceContextTextMapPropagator()


def setup_tracing(
    service_name: str,
    otlp_endpoint: str | None = None,
) -> None:
    """Initializes OpenTelemetry tracing with OTLP exporter and auto-instrumentation.

    Args:
        service_name: The logical name of the microservice.
        otlp_endpoint: OTLP collector gRPC endpoint. If None, uses env var
                        OTEL_EXPORTER_OTLP_ENDPOINT or defaults to localhost:4317.
    """
    endpoint = otlp_endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(
            "OTLP trace exporter configured",
            endpoint=endpoint,
            service=service_name,
        )
    except Exception as exc:
        logger.warn(
            "OTLP exporter unavailable — traces will not be exported",
            error=str(exc),
        )

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor().instrument()
        logger.info("FastAPI auto-instrumentation enabled")
    except Exception:
        pass

    # Auto-instrument SQLAlchemy
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy auto-instrumentation enabled")
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Trace Context Helpers
# ──────────────────────────────────────────────────────────────────────────────


def get_current_trace_context() -> dict[str, str]:
    """Returns a dict containing the current W3C traceparent header for propagation."""
    carrier: dict[str, str] = {}
    _propagator.inject(carrier)
    return carrier


def extract_trace_context(carrier: dict[str, str]) -> Context:
    """Extracts OTel context from a W3C traceparent carrier dict."""
    return _propagator.extract(carrier)


def get_current_ids() -> tuple[str, str]:
    """Returns (trace_id, span_id) hex strings from the current active span.

    Returns ("0", "0") if no span is active.
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
    return "0", "0"


# ──────────────────────────────────────────────────────────────────────────────
# Kafka Trace Propagation
# ──────────────────────────────────────────────────────────────────────────────


def inject_trace_into_event(event_dict: dict[str, Any]) -> dict[str, Any]:
    """Injects W3C trace context into a Kafka event payload dict."""
    carrier = get_current_trace_context()
    if carrier:
        event_dict["_trace_context"] = carrier
    return event_dict


def extract_trace_from_event(event_dict: dict[str, Any]) -> Context | None:
    """Extracts OTel context from a Kafka event payload dict."""
    carrier = event_dict.get("_trace_context")
    if carrier and isinstance(carrier, dict):
        return extract_trace_context(carrier)
    return None
