# CloudScale Commerce

![PR Validation](https://github.com/yashaskn8/cloudscale-commerce/actions/workflows/pr-validation.yml/badge.svg)
![DevSecOps](https://github.com/yashaskn8/cloudscale-commerce/actions/workflows/security-devsecops.yml/badge.svg)
![Release](https://github.com/yashaskn8/cloudscale-commerce/actions/workflows/release-cd.yml/badge.svg)
![EKS Deploy](https://github.com/yashaskn8/cloudscale-commerce/actions/workflows/aws-eks-deployment.yml/badge.svg)

**Production-grade distributed e-commerce platform** built with Clean Architecture, Domain-Driven Design, Event-Driven Architecture, and cloud-native best practices.

---

## Architecture

| Layer | Technology |
|---|---|
| **API Gateway** | Kong Ingress Controller (TLS, JWT, Rate Limiting) |
| **Microservices** | Python 3.12 / FastAPI / SQLAlchemy / Pydantic |
| **Messaging** | Apache Kafka (KRaft mode, Saga orchestration) |
| **Database** | PostgreSQL 15 (per-service isolation) |
| **Cache & Locks** | Redis 7 (cache-aside, distributed locking) |
| **Auth & Security** | Argon2id, JWT (access + refresh + rotation), RBAC |
| **Observability** | OpenTelemetry, Prometheus, Grafana, Jaeger, Loki |
| **Orchestration** | Kubernetes (Helm v3, HPAs, PDBs, NetworkPolicies) |
| **CI/CD** | GitHub Actions, Trivy, Bandit, Cosign, Semantic Versioning |
| **Cloud** | AWS (ECR, EKS, RDS, Secrets Manager, OIDC) |

## Services

| Service | Port | Responsibilities |
|---|---|---|
| `auth-service` | 8001 | Registration, login, JWT token management, RBAC |
| `catalog-service` | 8002 | Product CRUD, search, cache-aside reads |
| `inventory-service` | 8003 | Stock management, optimistic locking, reservations |
| `order-service` | 8004 | Checkout Saga coordinator, state machine |
| `payment-service` | 8005 | Event-driven payment processing |
| `notification-service` | 8006 | Email/SMS notification dispatch |

## Quick Start

### Local Development (Docker Compose)
```bash
docker compose up -d --build
```

### Kubernetes Deployment (Helm)
```bash
# Development
helm install cloudscale deployments/helm/cloudscale-parent -f deployments/helm/cloudscale-parent/values-dev.yaml

# Production
helm install cloudscale deployments/helm/cloudscale-parent -f deployments/helm/cloudscale-parent/values-prod.yaml
```

### Running Tests
```bash
# Unit tests (single service)
PYTHONPATH=services/auth pytest --asyncio-mode=auto services/auth/tests/

# Contract tests (requires running services)
pytest tests/contract/

# Smoke tests (post-deployment)
pytest tests/smoke/
```

## CI/CD Pipeline

| Workflow | Trigger | Purpose |
|---|---|---|
| `pr-validation.yml` | Pull Request | Ruff, Black, MyPy, parallel pytest |
| `security-devsecops.yml` | Push to main / PR | Bandit SAST, Trivy scans, SBOM, Helm lint |
| `release-cd.yml` | Push to main | Semantic versioning, ECR push, Helm publish |
| `aws-eks-deployment.yml` | Release / Manual | EKS rollout (Canary/Blue-Green), rollbacks |

## Branch Protection Recommendations

- Require **PR reviews** (≥1 approval) before merging to `main`.
- Require **status checks** to pass: `lint-and-format`, `test-services`, `sast-scan`, `helm-validation`.
- Require **signed commits**.
- Restrict **force pushes** to `main` and `develop`.
- Enable **Dependabot** vulnerability alerts and auto-merge for patch updates.

## License

Proprietary — CloudScale Commerce Platform.
