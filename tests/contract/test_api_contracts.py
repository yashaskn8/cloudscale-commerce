"""API Contract Tests — Validates microservice API response schemas and status codes.

These tests run against live (or staging) service endpoints to verify:
1. Health probe contracts.
2. HTTP status code correctness on standard endpoints.
3. Response body schema structure matches expected contracts.

Note: Tests gracefully skip when services are offline (httpx.ConnectError).
"""

import os

import httpx
import pytest

BASE_URLS = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://localhost:8001"),
    "catalog": os.getenv("CATALOG_SERVICE_URL", "http://localhost:8002"),
    "inventory": os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8003"),
    "order": os.getenv("ORDER_SERVICE_URL", "http://localhost:8004"),
    "payment": os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8005"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8006"),
}


def _get_or_skip(url: str, timeout: float = 5.0) -> httpx.Response:
    """Send GET request, skip test if service is unreachable."""
    try:
        return httpx.get(url, timeout=timeout)
    except httpx.ConnectError:
        pytest.skip(f"Service not reachable at {url}")


@pytest.mark.parametrize("service_name,base_url", BASE_URLS.items())
def test_liveness_probe_contract(service_name: str, base_url: str):
    """Verify /health/liveness returns 200 with expected JSON shape."""
    response = _get_or_skip(f"{base_url}/health/liveness")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["status"] == "alive"
    assert "service" in body


@pytest.mark.parametrize("service_name,base_url", BASE_URLS.items())
def test_readiness_probe_contract(service_name: str, base_url: str):
    """Verify /health/readiness returns 200 or 503 with checks dict."""
    response = _get_or_skip(f"{base_url}/health/readiness")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "status" in body
    assert "checks" in body
    assert isinstance(body["checks"], dict)


@pytest.mark.parametrize("service_name,base_url", BASE_URLS.items())
def test_metrics_endpoint_contract(service_name: str, base_url: str):
    """Verify /metrics returns Prometheus text format."""
    response = _get_or_skip(f"{base_url}/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "HELP" in response.text
