# CloudScale Commerce — AWS & Kubernetes Deployment Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [AWS Infrastructure](#aws-infrastructure)
4. [Kubernetes Cluster](#kubernetes-cluster)
5. [Helm Deployment](#helm-deployment)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [Disaster Recovery](#disaster-recovery)

---

## Architecture Overview

CloudScale Commerce is deployed as a set of containerized microservices on Amazon EKS (Elastic Kubernetes Service). The architecture follows a multi-AZ deployment pattern for high availability with the following topology:

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud (us-east-1)                   │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │ Route 53     │───▶│ CloudFront CDN (Static Assets)       │   │
│  │ DNS          │    └──────────────────────────────────────┘   │
│  └──────┬───────┘                                               │
│         │                                                       │
│  ┌──────▼───────┐    ┌──────────────────────────────────────┐   │
│  │ ALB          │───▶│ EKS Cluster                          │   │
│  │ (Ingress)    │    │  ┌────────────┐ ┌────────────┐       │   │
│  └──────────────┘    │  │ auth-svc   │ │ catalog-svc│       │   │
│                      │  ├────────────┤ ├────────────┤       │   │
│                      │  │ order-svc  │ │ payment-svc│       │   │
│                      │  ├────────────┤ ├────────────┤       │   │
│                      │  │ inv-svc    │ │ notif-svc  │       │   │
│                      │  └────────────┘ └────────────┘       │   │
│                      └──────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ RDS Aurora   │    │ ElastiCache  │    │ Amazon MSK   │       │
│  │ (PostgreSQL) │    │ (Redis)      │    │ (Kafka)      │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

| Tool        | Minimum Version | Purpose                      |
|-------------|-----------------|------------------------------|
| AWS CLI     | 2.15+           | Cloud resource provisioning  |
| kubectl     | 1.28+           | Kubernetes cluster control   |
| Helm        | 3.14+           | Chart-based deployments      |
| Terraform   | 1.7+            | Infrastructure as Code       |
| Docker      | 24.0+           | Container image builds       |
| eksctl      | 0.170+          | EKS cluster lifecycle        |

## AWS Infrastructure

### 1. VPC & Networking

```bash
# Create VPC with public/private subnets across 3 AZs
eksctl create cluster \
  --name cloudscale-prod \
  --region us-east-1 \
  --version 1.29 \
  --nodegroup-name workers \
  --node-type m6i.xlarge \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed \
  --vpc-cidr 10.0.0.0/16
```

### 2. RDS Aurora PostgreSQL

```bash
aws rds create-db-cluster \
  --db-cluster-identifier cloudscale-db \
  --engine aurora-postgresql \
  --engine-version 15.4 \
  --master-username cloudscale_admin \
  --master-user-password "${DB_PASSWORD}" \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name cloudscale-subnet \
  --storage-encrypted \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --deletion-protection

# Create read replica for CQRS read path
aws rds create-db-instance \
  --db-instance-identifier cloudscale-db-reader \
  --db-cluster-identifier cloudscale-db \
  --db-instance-class db.r6g.large \
  --engine aurora-postgresql
```

### 3. ElastiCache Redis

```bash
aws elasticache create-replication-group \
  --replication-group-id cloudscale-cache \
  --replication-group-description "CloudScale Redis cluster" \
  --engine redis \
  --engine-version 7.0 \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 3 \
  --automatic-failover-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --cache-subnet-group-name cloudscale-redis-subnet
```

### 4. Amazon MSK (Kafka)

```bash
aws kafka create-cluster \
  --cluster-name cloudscale-events \
  --kafka-version 3.6.0 \
  --number-of-broker-nodes 3 \
  --broker-node-group-info \
    '{"InstanceType":"kafka.m5.large","ClientSubnets":["subnet-a","subnet-b","subnet-c"],"SecurityGroups":["sg-kafka"],"StorageInfo":{"EbsStorageInfo":{"VolumeSize":100}}}' \
  --encryption-info \
    '{"EncryptionInTransit":{"ClientBroker":"TLS","InCluster":true}}'
```

## Kubernetes Cluster

### Namespace Setup

```bash
kubectl create namespace cloudscale-prod
kubectl create namespace cloudscale-staging
kubectl create namespace monitoring

# Apply resource quotas
kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: prod-quota
  namespace: cloudscale-prod
spec:
  hard:
    requests.cpu: "20"
    requests.memory: 40Gi
    limits.cpu: "40"
    limits.memory: 80Gi
    pods: "100"
EOF
```

### Secrets Management

```bash
# Store secrets in AWS Secrets Manager, synced via External Secrets Operator
kubectl apply -f - <<EOF
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: cloudscale-db-secret
  namespace: cloudscale-prod
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: database-credentials
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: cloudscale/prod/database
        property: url
    - secretKey: REDIS_URL
      remoteRef:
        key: cloudscale/prod/redis
        property: url
EOF
```

## Helm Deployment

```bash
# Deploy entire platform via parent chart
helm upgrade --install cloudscale \
  ./deployments/helm/cloudscale-parent \
  --namespace cloudscale-prod \
  --values ./deployments/helm/values-prod.yaml \
  --set global.image.tag=$(git rev-parse --short HEAD) \
  --set global.environment=production \
  --set global.replicas.auth=3 \
  --set global.replicas.catalog=3 \
  --set global.replicas.order=3 \
  --set global.replicas.payment=2 \
  --set global.replicas.inventory=2 \
  --set global.replicas.notification=2 \
  --wait --timeout 10m
```

### Health Verification

```bash
# Verify all pods are running
kubectl get pods -n cloudscale-prod -l app.kubernetes.io/part-of=cloudscale

# Check service endpoints
kubectl get endpoints -n cloudscale-prod

# Verify HPA is active
kubectl get hpa -n cloudscale-prod
```

## CI/CD Pipeline

The CI/CD pipeline uses GitHub Actions with the following stages:

| Stage       | Trigger        | Actions                                              |
|-------------|----------------|------------------------------------------------------|
| **Lint**    | Every push     | ESLint, Ruff, type-check, Prettier                   |
| **Test**    | Every push     | pytest (per-service), Vitest, Playwright              |
| **Build**   | PR merge       | Docker multi-stage builds, push to ECR                |
| **Deploy**  | Tag release    | Helm upgrade to staging → smoke tests → prod rollout  |
| **Rollback**| Manual/Alert   | Helm rollback to previous revision                    |

### Container Image Build

```dockerfile
# Multi-stage build for auth-service (representative pattern)
FROM python:3.12-slim AS builder
WORKDIR /app
COPY services/auth/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY shared/python /app/shared/python
COPY services/auth/app /app/app

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --from=builder /app .
ENV PYTHONPATH="/app:/app/shared/python"
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

## Monitoring & Alerting

### Prometheus + Grafana Stack

```bash
# Install kube-prometheus-stack via Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set grafana.adminPassword="${GRAFANA_PASSWORD}" \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi
```

### Key SLI/SLO Metrics

| Service       | SLI                            | SLO Target |
|---------------|--------------------------------|------------|
| Auth          | Login latency p99              | < 200ms    |
| Catalog       | Product list latency p95       | < 150ms    |
| Order         | Checkout saga completion p99   | < 2s       |
| Payment       | Payment processing p99         | < 3s       |
| Notification  | Event delivery latency p95     | < 500ms    |
| Overall       | Availability                   | 99.95%     |

### Alert Rules

```yaml
# Example: High error rate alert
groups:
  - name: cloudscale-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High 5xx error rate on {{ $labels.service }}"
          runbook: "https://wiki.internal/runbooks/high-error-rate"

      - alert: SagaCompletionSlow
        expr: histogram_quantile(0.99, rate(saga_duration_seconds_bucket[5m])) > 2
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Order saga p99 latency exceeding 2s SLO"
```

## Disaster Recovery

### Backup Strategy

| Component   | Method                      | Frequency   | Retention |
|-------------|-----------------------------|-------------|-----------|
| PostgreSQL  | Aurora automated snapshots  | Continuous  | 7 days    |
| PostgreSQL  | Cross-region replication    | Real-time   | Active    |
| Redis       | RDB snapshots               | Every 6h    | 3 days    |
| Kafka       | Topic replication factor 3  | Real-time   | Active    |
| Configs     | Git + Sealed Secrets        | Per-commit  | Forever   |

### RTO/RPO Targets

| Scenario              | RTO       | RPO        |
|-----------------------|-----------|------------|
| Single node failure   | < 30s     | 0 (HA)     |
| AZ failure            | < 5min    | 0 (Multi-AZ)|
| Region failure        | < 1hr     | < 5min     |
| Data corruption       | < 2hr     | < 1hr      |

### Failover Procedure

```bash
# 1. Verify health degradation
kubectl get pods -n cloudscale-prod --field-selector=status.phase!=Running

# 2. If full region failover is needed
aws rds failover-db-cluster --db-cluster-identifier cloudscale-db

# 3. Scale up in DR region
kubectl config use-context cloudscale-dr
helm upgrade --install cloudscale ./deployments/helm/cloudscale-parent \
  --namespace cloudscale-prod \
  --values ./deployments/helm/values-dr.yaml \
  --wait

# 4. Update DNS to point to DR region
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234 \
  --change-batch file://dr-dns-failover.json
```

---

> **Document Version**: 1.0.0  
> **Last Updated**: July 2026  
> **Author**: CloudScale Platform Engineering Team
