# Changelog

All notable changes to the CloudScale Commerce platform will be documented in this file.

---

## [1.0.0] — 2026-07-09

### Added
- **Core Microservices**: Auth, Catalog, Inventory, Order, Payment, and Notification services implemented using FastAPI.
- **Transactional Messaging**: Kafka choreographed Saga pattern with Inbox/Outbox deduplication.
- **Resiliency Framework**: Decorator-driven circuit breakers, exponential retries, and bulkhead limits.
- **Caching Tier**: L1 in-memory + L2 Redis cache-aside with Single-Flight stampede locks.
- **Infrastructure as Code**: Modular Terraform scripts for EKS, RDS, MSK, WAF, and VPC.
- **Observability**: OpenTelemetry tracing, Prometheus RED/USE metrics, Jaeger tracing, and SRE Grafana dashboards.
