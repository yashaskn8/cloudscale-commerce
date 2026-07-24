import pytest
from app.main import app
from cloudscale_shared.tracing import extract_trace_from_event, get_current_ids, inject_trace_into_event, setup_tracing
from httpx import ASGITransport, AsyncClient
from opentelemetry import trace


@pytest.fixture(scope="module", autouse=True)
def init_tracer():
    setup_tracing("test-observability-service")


def test_otel_tracing_setup():
    # Verify tracer provider is configured and returns a valid tracer instance
    tracer = trace.get_tracer("test-tracer")
    assert tracer is not None


def test_span_id_and_trace_id_extraction():
    tracer = trace.get_tracer("test-tracer")

    # Outside active span, should return '0', '0'
    t1, s1 = get_current_ids()
    assert t1 == "0"
    assert s1 == "0"

    # Inside active span, should return correct hex ID strings
    with tracer.start_as_current_span("test-active-span") as _:
        t2, s2 = get_current_ids()
        assert t2 != "0"
        assert s2 != "0"
        assert len(t2) == 32
        assert len(s2) == 16


def test_kafka_event_trace_propagation():
    tracer = trace.get_tracer("test-tracer")

    with tracer.start_as_current_span("test-publisher-span"):
        event = {"event_type": "TestEvent", "correlation_id": "test-corr-obs", "payload": {}}
        # Inject trace context
        injected_event = inject_trace_into_event(event)
        assert "_trace_context" in injected_event
        assert "traceparent" in injected_event["_trace_context"]

        # Extract trace context
        extracted_ctx = extract_trace_from_event(injected_event)
        assert extracted_ctx is not None


@pytest.mark.asyncio
async def test_health_check_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Liveness check
        res_liveness = await client.get("/health/liveness")
        assert res_liveness.status_code == 200
        assert res_liveness.json()["status"] == "alive"

        # Readiness check (DB & Redis configured to test engine)
        res_readiness = await client.get("/health/readiness")
        assert res_readiness.status_code in (200, 503)
        assert "status" in res_readiness.json()
        assert "checks" in res_readiness.json()
