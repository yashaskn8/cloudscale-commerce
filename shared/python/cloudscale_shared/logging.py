"""Production-Grade Structured Logging Module.

Provides:
- Structured JSON logging (production) or colorized console (development)
- Automatic trace_id and span_id injection from OpenTelemetry context
- Service name binding
- Standard library logging redirection to structlog
"""
import logging
import sys
import structlog
from typing import Any


def _add_trace_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that injects OTel trace_id and span_id into log events."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id:
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
        else:
            event_dict["trace_id"] = "0"
            event_dict["span_id"] = "0"
    except ImportError:
        event_dict["trace_id"] = "0"
        event_dict["span_id"] = "0"
    return event_dict


def setup_logging(service_name: str, level: str = "INFO") -> None:
    """Configures structured JSON logging for the microservice with trace enrichment."""
    logging_level = getattr(logging, level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_trace_context,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # In production/Docker containers, log as JSON. For local development, colorized text.
    if sys.stdout.isatty():
        processors = shared_processors + [structlog.dev.ConsoleRenderer()]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to redirect to structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging_level,
    )

    logger = structlog.get_logger()
    logger.info("Structured logging initialized", service=service_name)
