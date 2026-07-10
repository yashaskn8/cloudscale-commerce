# CloudScale Commerce - Developer Guide

Welcome to the CloudScale Commerce workspace! This guide outlines local setups, development standards, database migrations, and testing strategies for our distributed cloud-native platform.

---

## 1. Local Development Quickstart

### Prerequisites
* **Python**: Python 3.12+
* **Container Tooling**: Docker and Docker Compose (highly recommended)

### Step 1: Run Infrastructure Dependencies
To start PostgreSQL databases, Redis cache, Kafka broker, and the Kong Gateway, run:
```bash
docker compose up -d postgres redis kafka kong
```

### Step 2: Set up Local Python Environment
Create a virtual environment and install the shared libraries in editable mode along with service requirements:
```bash
python -m venv .venv
# On Windows Powershell:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install shared package
pip install -e shared/python

# Install service-specific dependencies (example for Auth service)
pip install -r services/auth/requirements.txt
```

### Step 3: Run Services Locally
Run any service using `uvicorn` (ensure you pass correct database/broker urls if running outside docker compose):
```bash
# Running Auth Service locally
cd services/auth
uvicorn app.main:app --port 8001 --reload
```

---

## 2. API Gateway Routing
When containers are running via docker-compose, the **Kong API Gateway** acts as the single boundary ingress terminated on port `8000`. 
* **Identity Router**: `http://localhost:8000/api/v1/auth/*`
* **Catalog Router**: `http://localhost:8000/api/v1/products/*`
* **Inventory Router**: `http://localhost:8000/api/v1/inventory/*`
* **Order Router**: `http://localhost:8000/api/v1/orders/*`

---

## 3. Database Migrations (Alembic)

Each database-connected microservice (`auth`, `catalog`, `inventory`, `order`) is configured with its own Alembic workspace. Migrations read credentials dynamically from environment configs.

### Run Migrations to Latest Schema
From the microservice root folder (e.g., `services/auth`):
```bash
# Run migrations up to latest revision
alembic upgrade head
```

### Create a New Schema Migration
If you modify any SQLAlchemy model in `app/models.py`, generate a new migration script using auto-generation:
```bash
# Run auto-generate revision script
alembic revision --autogenerate -m "Add new attributes"
```

---

## 4. Sync Communication (gRPC Protobufs)
gRPC definitions are located in [shared/proto/](file:///c:/Users/prana/OneDrive/Desktop/enterpise/shared/proto/). To recompile python proto classes following modifications:
```bash
pip install grpcio-tools
python -m grpc_tools.protoc -Ishared/proto --python_out=shared/python/cloudscale_shared --grpc_python_out=shared/python/cloudscale_shared shared/proto/*.proto
```

---

## 5. Verifying the Event-Driven Saga
The checkout lifecycle is managed by an eventual-consistent transaction Saga:
```
[POST /orders] -> Order (PENDING) -> Kafka: OrderCreatedEvent
                                      │
  ┌───────────────────────────────────┘
  ▼
[Inventory Service] -> Locks Redis -> Reserve Stock -> Kafka: InventoryReservedEvent
                                                                 │
  ┌──────────────────────────────────────────────────────────────┘
  ▼
[Payment Service] -> Simulates card charge -> Kafka: PaymentSuccessEvent / PaymentFailedEvent
                                                        │
  ┌─────────────────────────────────────────────────────┴───────────┐
  ▼                                                                 ▼
[Order Service] -> status=CONFIRMED                              [Order Service] -> status=CANCELLED
[Notification Service] -> Send Receipt Email                      Kafka: OrderCancelledEvent
                                                                    │
                                                                    ▼
                                                                 [Inventory Service] -> Release Stock
```

### Saga Verification Test Case
1. **Deduct Stock**: Place an order for quantity = `1`. Verify status changes to `CONFIRMED` in the Order database and stock reserves.
2. **Rollback Stock**: Place an order for quantity = `99` (simulated payment decline hook). Verify order changes to `CANCELLED` and stock releases back to inventory database.
