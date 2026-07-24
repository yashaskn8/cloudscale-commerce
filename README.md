# CloudScale Commerce

<p align="center">
  <img src="docs/architecture/workflow_diagram.png" alt="CloudScale Commerce Workflow" width="800">
</p>

[![CI/CD Validation](https://github.com/yashaskn8/cloudscale-commerce/actions/workflows/pr-validation.yml/badge.svg)](.github/workflows/pr-validation.yml)
[![Security Scan](https://github.com/yashaskn8/cloudscale-commerce/actions/workflows/security-devsecops.yml/badge.svg)](.github/workflows/security-devsecops.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, multi-tenant, event-driven e-commerce microservices platform built with **Python 3.12 (FastAPI)**, **PostgreSQL**, **Apache Kafka**, **Redis**, and **Kubernetes**. 

This repository implements production-grade distributed systems patterns designed to solve data consistency, race conditions, tenant isolation, and security at scale.

---

## Architecture Overview

```mermaid
graph TD
    Client[Client Browser / Frontend] --> Ingress[Nginx Ingress / Api Gateway]
    
    subgraph K8s [Kubernetes / Helm Orchestration]
        Ingress --> Auth[auth-service:8001]
        Ingress --> Catalog[catalog-service:8002]
        Ingress --> Inventory[inventory-service:8003]
        Ingress --> Order[order-service:8004]
        
        Catalog -.-> Redis[(Redis 7 Cache)]
        
        %% Database Layer
        Auth --> AuthDB[(Auth PostgreSQL)]
        Catalog --> CatalogDB[(Catalog PostgreSQL)]
        Inventory --> InvDB[(Inventory PostgreSQL)]
        Order --> OrderDB[(Order PostgreSQL)]
        
        %% Event Stream
        Order -- Writes Outbox --> Kafka[Apache Kafka Cluster]
        Kafka -- Consumes Events --> Payment[payment-service:8005]
        Kafka -- Consumes Events --> Notification[notification-service:8006]
        
        Payment --> PayDB[(Payment PostgreSQL)]
        Notification --> NotifDB[(Notification PostgreSQL)]
    end
```

### Microservices Catalog
1. **[Auth Service](services/auth)**: Handles user registration, Argon2id password hashing, JWT token rotation, and Role-Based Access Control (RBAC).
2. **[Catalog Service](services/catalog)**: Manages product inventories and handles product search using a TF-IDF lexical search engine with hash-projected vectors and manual query expansion.
3. **[Inventory Service](services/inventory)**: Controls product stocks, manages reservations, and enforces concurrency limits.
4. **[Order Service](services/order)**: Acts as the checkout Saga coordinator, directing multi-stage transactional checkout states.
5. **[Payment Service](services/payment)**: Implements a simulated payment flow with a documented extension point for real Stripe integration (controlled by `SIMULATE_PAYMENTS` flag).
6. **[Notification Service](services/notification)**: Dispatches transactional order updates (currently simulated for local/staging deployments).

---

## Architectural & Distributed Systems Patterns

### 1. Transactional Outbox & Inbox Patterns
To avoid dual-write failures (e.g., updating a database but failing to notify Kafka), services implement the **Transactional Outbox Pattern**:
* **Outbox Publish**: Domain state updates and outbound event creation are written to the database within a single local ACID transaction using [write_outbox()](shared/python/cloudscale_shared/outbox.py).
* **Outbox Worker**: An asynchronous background loop [OutboxWorker](shared/python/cloudscale_shared/outbox.py) polls the outbox table, publishes events to Kafka with at-least-once delivery guarantees, and marks them processed.
* **Inbox Deduplication**: Consumers leverage [inbox_already_processed()](shared/python/cloudscale_shared/inbox.py) to prevent duplicate processing (exactly-once processing semantics at the application boundary).

### 2. Sagas (Choreographed Saga State Machine)
The checkout pipeline coordinates distributed transactions across Order, Inventory, and Payment services using a reactive state machine:
```
  [Order PENDING] ──► (InventoryReservedEvent) ──► [STOCK_RESERVED]
  [STOCK_RESERVED] ──► (PaymentSuccessEvent) ──► [CONFIRMED]
  
  %% Compensation flows
  [PENDING] ──► (InventoryReserveFailedEvent) ──► [CANCELLED_NO_STOCK]
  [STOCK_RESERVED] ──► (PaymentFailedEvent) ──► [CANCELLED] ──► Trigger Stock Release
```

### 3. PostgreSQL Row-Level Security (RLS)
Tenant-level data isolation is enforced at the database driver boundary using native PostgreSQL policies:
* Multi-tenant tables are secured via [v2_postgresql_rls_migration.py](shared/python/cloudscale_shared/v2_postgresql_rls_migration.py).
* SQLAlchemy sessions set connection-level context (`app.current_tenant_id`) via `set_config()` at the start of each transaction when connecting to PostgreSQL.
* Services connect as a restricted `cloudscale_app` database role (non-superuser) so that `FORCE ROW LEVEL SECURITY` policies are enforced by PostgreSQL.

### 4. Optimistic Concurrency Control (OCC)
In high-concurrency settings (such as flash sales), the [Inventory](services/inventory/app/models.py) model implements version-based optimistic locking (`version_id_col`) to prevent double-allocations and race conditions without blocking database threads.

---

## Infrastructure & DevSecOps

### CI/CD Workflows
* **[Pull Request Validation](.github/workflows/pr-validation.yml)**: Runs linting (Ruff, Black), strict type checks (Mypy), and parallel unit testing. Connects automatically to a real `postgres:15-alpine` container to ensure migration compatibility.
* **[DevSecOps Pipeline](.github/workflows/security-devsecops.yml)**: Scans for vulnerabilities via Bandit (SAST) and Trivy (container image layers), produces SPDX SBOM files, and performs keyless image signing via **Cosign** (Fulcio/Rekor).
* **[Continuous Deployment](.github/workflows/aws-eks-deployment.yml)**: Automates canary-based rollouts to AWS EKS with post-deployment functional smoke testing gates.

### Kubernetes Deployment
* **Helm v3 Charts**: The parent chart [cloudscale-parent](deployments/helm/cloudscale-parent) configures microservices dynamically using structured profiles (`values-dev.yaml`, `values-staging.yaml`, `values-prod.yaml`).
* Features pre-configured horizontal pod autoscalers (HPAs), network policies, and pod disruption budgets.

---

## Setup & Execution

### 1. Local Run (Docker Compose)
Spins up PostgreSQL instances, Apache Kafka, Redis, and all microservices:
```bash
docker compose up -d --build
```

### 2. Environment Setup
Some services require environment variables. Copy the example files or export them manually:
```bash
# Option A: Copy .env.example files (auth and payment have required secrets)
cp services/auth/.env.example services/auth/.env
cp services/payment/.env.example services/payment/.env

# Option B: Export directly for quick testing
export JWT_SECRET_KEY="your-secret-key-min-32-chars-long"
export STRIPE_WEBHOOK_SECRET="whsec_test_secret"
```
> **Note**: Without `JWT_SECRET_KEY`, auth service tests will fail with `pydantic.ValidationError`.

### 3. Install Shared Library & Run Tests
```bash
# Install the shared Python package (required before running any service tests)
pip install -e ./shared/python

# Run ALL service tests with a single command (recommended)
make test

# Or run a single service's tests
make test-auth
make test-order

# Or run manually with required env vars
JWT_SECRET_KEY=test-secret-key-for-ci-32chars \
  PYTHONPATH=services/auth pytest services/auth/tests/
```

---

## Software Engineering Guidelines & Compliance
* **Type Safety**: Enforced strict annotations across shared modules and services checked by Mypy.
* **Code Style**: Zero-warnings policy enforced via Ruff.
* **Change Log**: Follows Semantic Versioning rules tracked in the [CHANGELOG](CHANGELOG.md).
