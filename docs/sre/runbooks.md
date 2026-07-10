# CloudScale Commerce — SRE Runbooks & Disaster Recovery (DR)

This documentation provides operational guides for SREs, platform engineers, and developers managing the production-grade e-commerce stack.

---

## 1. Incident Response Plan

1. **Detection**: Alerts routed from Prometheus Alertmanager to PagerDuty/Slack.
2. **Triage**: Identify affected service via Grafana RED dashboards and Jaeger traces.
3. **Mitigation**: Route traffic away (Kong redirect), scale up replicas, or rollback.
4. **Resolution**: Deploy fix, patch config, or restore database from backup.
5. **Post-Mortem**: Conduct root cause analysis (RCA) and document corrective actions.

---

## 2. Disaster Recovery Strategy (RTO / RPO)

- **RTO (Recovery Time Objective)**: 15 Minutes. Target time to restore full service operational status after a critical cluster blackout.
- **RPO (Recovery Point Objective)**: 5 Minutes. Target maximum data loss interval in the event of database hardware failure.

### Relational Database (PostgreSQL) Backup & Restore
- **Backup**: Run pg_dump automatically every hour to an offsite S3 bucket:
  ```bash
  pg_dump -U postgres -h postgres.cloudscale.internal -d auth_db | gzip > auth_db_$(date +%F_%T).sql.gz
  ```
- **Restore**: Spin up clean database pod, copy backup file, and run:
  ```bash
  gunzip -c auth_db_backup.sql.gz | psql -U postgres -h postgres.cloudscale.internal -d auth_db
  ```

---

## 3. Stateful Service Recovery Runbooks

### Kafka Broker Failure & Replay
1. **Scenario**: A broker node fails and partition replicas become out of sync.
2. **Mitigation**:
   - Check broker statuses using `kafka-topics.sh` or lag metrics in Grafana.
   - Force leader reelection using:
     ```bash
     kafka-leader-election.sh --bootstrap-server kafka:9092 --election-type preferred --all-topic-partitions
     ```
   - **Replay**: To replay messages from a specific timestamp, adjust consumer group offsets:
     ```bash
     kafka-consumer-groups.sh --bootstrap-server kafka:9092 --group order-service-group --reset-offsets --to-datetime 2026-07-09T00:00:00.000 --execute --topic orders
     ```

### Redis Outage & Persistence Re-warming
1. **Scenario**: Redis container crashes, causing cache-aside calls to fall back to Postgres.
2. **Mitigation**:
   - Ensure AOF (Append Only File) is enabled in `/data/redis.conf` for persistent keys (e.g. rate limit blocks).
   - In the event of cold startup, warm critical caches (e.g. products) using catalog warming script to avoid database stampedes.

---

## 4. Kubernetes Scaling & Rollback Procedures

### Manual Rollback
If a deployment triggers high latencies or HTTP 5xx error alerts, roll back immediately:
```bash
# Roll back EKS deployment using Helm
helm rollback cloudscale --namespace cloudscale-prod

# If using blue-green ingress, swap traffic back to stable blue slice
kubectl patch ingress cloudscale-ingress -n cloudscale-prod \
  --type=json -p='[{"op": "replace", "path": "/spec/rules/0/http/paths/0/backend/service/name", "value": "cloudscale-blue-service"}]'
```

### HPA Tuning & Scaling
- HPAs are configured to scale up dynamically when CPU utilization hits **70%** or Memory utilization hits **80%**.
- SREs can override limits in `values-prod.yaml` or scale deployments manually:
  ```bash
  kubectl scale deployment cloudscale-order-service --replicas=10 -n cloudscale-prod
  ```
