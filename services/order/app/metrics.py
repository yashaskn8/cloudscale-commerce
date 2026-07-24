"""Order Service — Low-Cardinality Prometheus Metrics.

Uses centralized metrics from cloudscale_shared.metrics alongside service-specific metrics.
"""

from cloudscale_shared.metrics import ORDERS_CREATED
from prometheus_client import Counter, Gauge

ORDERS_REVENUE_TOTAL = Counter("orders_revenue_total", "Total accumulated order revenue")
ACTIVE_SAGAS = Gauge("active_sagas", "Active checkout sagas")
PENDING_SAGAS = Gauge("pending_sagas", "Pending checkout sagas")
STALE_ORDERS_TOTAL = Counter("stale_orders_total", "Total orders timed out by sweeper")
