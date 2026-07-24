# CloudScale Commerce — Performance Benchmarks

This document describes how to run load tests against the CloudScale Commerce platform and capture baseline metrics. **No pre-computed benchmark numbers are included** — all metrics must be generated from actual test runs against the running Docker Compose stack.

---

## 1. Load Test Tool

We use [k6](https://k6.io/) for load testing. The workload script is located at `tests/performance/k6_workload.js`.

### Prerequisites
```bash
# Install k6 (macOS)
brew install k6

# Install k6 (Linux)
sudo apt-get install k6

# Or via Docker
docker run --rm -i grafana/k6 run - <tests/performance/k6_workload.js
```

---

## 2. Running Benchmarks

### Step 1: Start the full stack
```bash
docker compose up -d --build
```

### Step 2: Wait for all services to be healthy
```bash
docker compose ps
```

### Step 3: Run the k6 workload
```bash
k6 run --out json=tests/performance/results.json tests/performance/k6_workload.js
```

### Step 4: Capture results
The raw JSON output at `tests/performance/results.json` is the authoritative source for any metrics cited in documentation. Commit this file alongside any claims.

---

## 3. Metrics to Capture

| Metric | Description | How to Read |
|---|---|---|
| **http_req_duration (p50)** | Median request latency | `k6` summary output |
| **http_req_duration (p95)** | 95th percentile latency | `k6` summary output |
| **http_req_duration (p99)** | 99th percentile latency | `k6` summary output |
| **http_reqs** | Total requests per second (RPS) | `k6` summary output |
| **http_req_failed** | Error rate | `k6` summary output |

---

## 4. Chaos Testing

For resilience validation under failure conditions:

```bash
# Kill a service container mid-saga to test compensation
docker kill cloudscale-inventory-service

# Observe order service logs for compensating transaction
docker logs cloudscale-order-service --follow

# Restart the killed service
docker compose up -d inventory-service
```

For network partition simulation, use [toxiproxy](https://github.com/Shopify/toxiproxy):
```bash
# Add latency to postgres connections
toxiproxy-cli toxic add -t latency -a latency=5000 postgres_proxy

# Verify circuit breakers activate
curl http://localhost:8002/api/v1/products
```

---

## 5. Rules for Documenting Results

1. **No number without a file backing it.** Every metric cited in docs must reference a committed `results.json` file.
2. **Include test conditions.** Document the number of virtual users, duration, and hardware specs.
3. **Date the results.** Benchmarks become stale; always include the date and commit SHA.
