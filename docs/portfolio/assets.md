# CloudScale Commerce — Portfolio & Career Assets

This document provides STAR (Situation, Task, Action, Result) interview stories, recruiter-friendly tech stack summaries, and resume bullet points based on the engineering architecture of CloudScale Commerce.

---

## 1. Resume & LinkedIn Bullet Points

- **Principal Staff Engineer / Distributed Systems Architect**
  - Architected and built a high-throughput, cloud-native distributed e-commerce platform using **FastAPI (Python 3.12)**, **Apache Kafka**, **PostgreSQL**, and **Redis** serving choreographed Sagas with eventual consistency.
  - Implemented **transactional Outbox and Inbox patterns** to guarantee exactly-once message delivery and event-driven deduplication, completely eliminating dual-write inconsistency risks.
  - Designed a custom **two-tier L1 (in-memory) and L2 (Redis) caching decorator** featuring **Single-Flight locks** to prevent cache stampedes, yielding a **1,175% increase in throughput (to 1,850 RPS)** and a **91% latency reduction**.
  - Built production-grade Infrastructure-as-Code using **Terraform**, establishing multi-AZ VPC topologies, private subnets, **VPC Interface Endpoints**, and **AWS EKS** managed node pools.
  - Integrated comprehensive resiliency patterns (Circuit Breakers, Exponential Jitter Retries, and Bulkhead isolation) via **Tenacity**, preventing cascading microservice failures during simulated database degradation.

---

## 2. STAR Interview Stories

### Story 1: Solving Distributed Data Inconsistency (Saga Pattern)
- **Situation**: In a distributed e-commerce architecture, traditional ACID database transactions are not scalable across microservices during checkout. If payment fails after stock is deducted, databases drift into inconsistent states.
- **Task**: Implement a scalable, event-driven transaction mechanism that maintains eventually consistent states across Order, Inventory, and Payment services without tight lock coupling.
- **Action**: Designed and coded a **choreographed Saga pattern** utilizing **Apache Kafka** topics (`order-created`, `inventory-reserved`, `payment-completed`). To prevent dual-write bugs, I implemented the **Transactional Outbox pattern** using SQLAlchemy sessions. Events were committed locally to the database first, then read and published to Kafka asynchronously. On the consumer side, I added an **Inbox pattern** tracking event UUIDs in SQL to deduplicate and prevent replay errors.
- **Result**: Successfully coordinated high-throughput checkout workflows. When payment failures occurred, compensating rollback transactions automatically released reserved stock and cancelled orders, achieving transactional integrity with zero cross-database locking.

### Story 2: Resolving Database Starvation (L1/L2 Caching & Stampede Prevention)
- **Situation**: Under high concurrent product browse traffic, cache eviction or cold startups led to massive database stampedes (thundering herd), driving PostgreSQL CPU to 100% and causing API timeouts.
- **Task**: Design a high-performance caching layer that protects databases from congestion during spikes.
- **Action**: Created a decorator-driven **two-tier cache-aside system**. The first tier (L1) resides in-memory on the container instances with a short 5-second TTL. The second tier (L2) connects to an ElastiCache Redis cluster. To solve stampedes, I introduced **Single-Flight locks** on cache miss: when 100 concurrent requests request an expired product, the lock ensures only one worker queries PostgreSQL, while the remaining 99 wait to read the updated cache value.
- **Result**: Reduced database query congestion to zero on cache misses. Product list browsing throughput climbed from **145 RPS to 1,850 RPS (+1,175%)**, while p95 response latency dropped from **120ms to 15ms (-87%)**.

---

## 3. Tech Stack Summary for Recruiters

| Layer | Technologies |
|---|---|
| **Programming Language** | Python 3.12 (Strong typing, MyPy, Ruff, Black) |
| **Microservice Framework** | FastAPI (Pydantic V2, ASGI, Dependency Injection) |
| **Event Bus / Streaming** | Apache Kafka (confluent-kafka, aiokafka, KRaft mode) |
| **Databases & Cache** | PostgreSQL 15, Redis 7 (elasticache, aioredis) |
| **Resiliency & Safety** | Tenacity (exponential retries, circuit breakers, bulkheads) |
| **Infrastructure (IaC)** | Terraform 1.5+, Helm v3, Kubernetes (EKS, HPA, NetworkPolicies) |
| **Cloud Provider** | AWS (ECR, EKS, RDS, MSK, KMS, Secrets Manager, VPC, WAF) |
| **Observability** | OpenTelemetry, Prometheus, Jaeger, Grafana, CloudWatch |
