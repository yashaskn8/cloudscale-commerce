# CloudScale Commerce — SRE Scaling & Operations Handbook

## Table of Contents
1. [Service Catalog](#service-catalog)
2. [On-Call Runbooks](#on-call-runbooks)
3. [Scaling Playbooks](#scaling-playbooks)
4. [Incident Response](#incident-response)
5. [Capacity Planning](#capacity-planning)
6. [Performance Benchmarks](#performance-benchmarks)

---

## Service Catalog

| Service        | Port  | Healthcheck          | Owner          | Criticality |
|----------------|-------|----------------------|----------------|-------------|
| auth-service   | 8001  | `/health`            | Platform Team  | P0          |
| catalog-service| 8002  | `/health`            | Commerce Team  | P0          |
| order-service  | 8003  | `/health`            | Commerce Team  | P0          |
| payment-service| 8004  | `/health`            | Payments Team  | P0          |
| inventory-svc  | 8005  | `/health`            | Supply Team    | P1          |
| notification   | 8006  | `/health`            | Platform Team  | P1          |
| api-gateway    | 8080  | `/health`            | Platform Team  | P0          |
| frontend       | 3000  | HTTP 200 on `/`      | Frontend Team  | P0          |

### Dependency Graph

```
frontend → api-gateway → auth-service
                        → catalog-service → PostgreSQL, Redis
                        → order-service   → PostgreSQL, Kafka, Redis
                        → payment-service → PostgreSQL, Stripe API
                        → inventory-svc   → PostgreSQL, Kafka
                        → notification    → Kafka, WebSocket
```

## On-Call Runbooks

### Runbook: Auth Service Unresponsive

**Symptoms**: Login failures, 503 on `/api/v1/auth/*`, JWT validation timeouts

**Diagnosis**:
```bash
# 1. Check pod status
kubectl get pods -n cloudscale-prod -l app=auth-service

# 2. Check recent logs
kubectl logs -n cloudscale-prod -l app=auth-service --tail=100 --since=5m

# 3. Check database connectivity
kubectl exec -n cloudscale-prod deploy/auth-service -- python -c "
from app.config import Settings
import asyncio, asyncpg
async def check():
    conn = await asyncpg.connect(Settings().database_url)
    print(await conn.fetchval('SELECT 1'))
    await conn.close()
asyncio.run(check())
"

# 4. Check Redis connectivity for token cache
kubectl exec -n cloudscale-prod deploy/auth-service -- python -c "
import redis
r = redis.from_url('redis://cloudscale-cache:6379')
print('PING:', r.ping())
"
```

**Resolution**:
1. If OOMKilled → Increase memory limits in Helm values
2. If database connection pool exhausted → Restart pods with `kubectl rollout restart`
3. If Redis timeout → Check ElastiCache metrics, failover if primary unhealthy
4. If persistent → Escalate to Platform Team lead

---

### Runbook: Kafka Consumer Lag

**Symptoms**: Order processing delays, notification delivery lag, increasing consumer group lag

**Diagnosis**:
```bash
# Check consumer group lag
kafka-consumer-groups.sh --bootstrap-server $KAFKA_BROKERS \
  --group order-processor --describe

# Check topic partition health
kafka-topics.sh --bootstrap-server $KAFKA_BROKERS \
  --describe --topic order-events
```

**Resolution**:
1. If lag < 1000 messages → Monitor, likely transient
2. If lag > 10000 → Scale consumer replicas: `kubectl scale deploy/order-service --replicas=5`
3. If specific partition stuck → Check for poison messages, route to DLQ
4. If broker unhealthy → Trigger MSK failover

---

### Runbook: Order Saga Stuck

**Symptoms**: Orders stuck in `PENDING` state, saga timeout alerts

**Diagnosis**:
```bash
# Check saga state in database
kubectl exec -n cloudscale-prod deploy/order-service -- python -c "
from app.config import Settings
import asyncio, asyncpg
async def check():
    conn = await asyncpg.connect(Settings().database_url)
    rows = await conn.fetch('''
        SELECT id, status, created_at
        FROM orders
        WHERE status = 'PENDING'
        AND created_at < NOW() - INTERVAL '10 minutes'
        ORDER BY created_at
        LIMIT 20
    ''')
    for r in rows:
        print(f'{r[\"id\"]} - {r[\"status\"]} - {r[\"created_at\"]}')
    await conn.close()
asyncio.run(check())
"

# Check compensation events
kubectl logs -n cloudscale-prod -l app=order-service --tail=200 | grep "compensation"
```

**Resolution**:
1. Check payment-service health — most saga failures originate from payment timeouts
2. If payment-service healthy → Check inventory reservation failures
3. Trigger manual compensation: POST `/api/v1/orders/{id}/compensate`
4. For stuck sagas > 1hr → Mark as FAILED and notify customer

---

## Scaling Playbooks

### Horizontal Pod Autoscaler Configuration

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: catalog-service-hpa
  namespace: cloudscale-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: catalog-service
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 75
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 25
          periodSeconds: 120
```

### Scaling Thresholds by Service

| Service         | Min Pods | Max Pods | Scale-Up Trigger          | Scale-Down Window |
|-----------------|----------|----------|---------------------------|-------------------|
| auth-service    | 3        | 15       | CPU > 60% or RPS > 500    | 5 min             |
| catalog-service | 3        | 20       | CPU > 65% or RPS > 200    | 5 min             |
| order-service   | 3        | 15       | CPU > 70% or Saga backlog | 5 min             |
| payment-service | 2        | 10       | CPU > 50% (payment-critical)| 10 min          |
| inventory-svc   | 2        | 8        | CPU > 70%                 | 5 min             |
| notification    | 2        | 10       | WS connections > 5000     | 5 min             |

### Database Scaling

```bash
# Vertical scaling (minimal downtime with Aurora)
aws rds modify-db-instance \
  --db-instance-identifier cloudscale-db-writer \
  --db-instance-class db.r6g.2xlarge \
  --apply-immediately

# Add read replicas for read-heavy workloads
aws rds create-db-instance \
  --db-instance-identifier cloudscale-db-reader-2 \
  --db-cluster-identifier cloudscale-db \
  --db-instance-class db.r6g.xlarge \
  --engine aurora-postgresql
```

## Incident Response

### Severity Levels

| Level | Description                                    | Response Time | Escalation     |
|-------|------------------------------------------------|---------------|----------------|
| SEV-1 | Platform-wide outage, data loss risk           | 5 min         | VP Engineering |
| SEV-2 | Single service down, degraded user experience  | 15 min        | Team Lead      |
| SEV-3 | Non-critical feature broken, workaround exists | 1 hr          | On-call        |
| SEV-4 | Minor bug, cosmetic issue                      | Next sprint   | Backlog        |

### Incident Timeline Template

```markdown
## Incident: [TITLE]
**Severity**: SEV-[1-4]
**Duration**: [START] → [END]
**Impact**: [User-facing impact description]

### Timeline
- HH:MM — Alert triggered: [description]
- HH:MM — On-call acknowledged
- HH:MM — Root cause identified: [description]
- HH:MM — Mitigation applied: [action taken]
- HH:MM — Service restored
- HH:MM — Post-incident review scheduled

### Root Cause
[Detailed technical explanation]

### Action Items
- [ ] [Preventive action 1]
- [ ] [Preventive action 2]
- [ ] [Detection improvement]
```

## Capacity Planning

### Current Resource Allocation (Production)

| Resource        | Current    | Peak Usage | Headroom | Next Threshold   |
|-----------------|------------|------------|----------|------------------|
| EKS Nodes       | 3× m6i.xl | 62% CPU    | 38%      | Add node at 75%  |
| RDS Aurora       | r6g.large  | 45% CPU    | 55%      | Scale at 70%     |
| ElastiCache     | r6g.large  | 30% memory | 70%      | Scale at 65%     |
| MSK Kafka       | m5.large   | 40% disk   | 60%      | Expand at 70%    |

### Growth Projections

| Metric              | Current  | +3 months | +6 months | +12 months |
|---------------------|----------|-----------|-----------|------------|
| Active tenants      | 50       | 200       | 500       | 2,000      |
| Products (total)    | 5,000    | 25,000    | 100,000   | 500,000    |
| Orders/day          | 500      | 2,000     | 8,000     | 50,000     |
| API requests/sec    | 50       | 200       | 800       | 5,000      |
| WebSocket conns     | 100      | 500       | 2,000     | 10,000     |

## Performance Benchmarks

### Load Test Results (k6, 100 concurrent users, 5 minutes)

| Endpoint                     | p50    | p95    | p99    | Throughput  | Error Rate |
|------------------------------|--------|--------|--------|-------------|------------|
| POST /auth/login             | 45ms   | 120ms  | 180ms  | 850 rps     | 0.01%      |
| GET /catalog/products        | 12ms   | 35ms   | 65ms   | 2,400 rps   | 0.00%      |
| GET /catalog/products/{id}   | 8ms    | 22ms   | 40ms   | 3,200 rps   | 0.00%      |
| POST /orders/checkout        | 180ms  | 450ms  | 890ms  | 220 rps     | 0.05%      |
| GET /orders                  | 25ms   | 60ms   | 110ms  | 1,600 rps   | 0.00%      |
| GET /inventory/{product_id}  | 10ms   | 28ms   | 50ms   | 2,800 rps   | 0.00%      |
| POST /payments/process       | 320ms  | 780ms  | 1.2s   | 150 rps     | 0.08%      |

### Resource Consumption Per Pod (Steady State)

| Service         | CPU (avg) | Memory (avg) | CPU (peak) | Memory (peak) |
|-----------------|-----------|--------------|------------|---------------|
| auth-service    | 120m      | 180Mi        | 350m       | 280Mi         |
| catalog-service | 80m       | 150Mi        | 250m       | 240Mi         |
| order-service   | 150m      | 200Mi        | 400m       | 320Mi         |
| payment-service | 100m      | 160Mi        | 300m       | 260Mi         |
| inventory-svc   | 60m       | 120Mi        | 200m       | 200Mi         |
| notification    | 90m       | 140Mi        | 280m       | 250Mi         |

---

> **Document Version**: 1.0.0  
> **Last Updated**: July 2026  
> **Author**: CloudScale SRE Team
