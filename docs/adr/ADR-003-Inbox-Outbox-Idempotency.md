# Architectural Decision Record — ADR-003: Inbox & Outbox Transactional Patterns

## Context & Problem
Dual-write scenarios (writing to database and publishing to Kafka) suffer from inconsistency. If database transaction commits but network fails before Kafka publish, messages are lost. If Kafka publishes but database rollback occurs, phantom messages propagate.

## Options Considered
1. **At-Least-Once raw publish**: High risk of duplicate events or message dropouts.
2. **Distributed Transactions (XA)**: Complex setup with high performance costs.
3. **Inbox & Outbox Patterns**: Save state and event inside the same local database transaction boundary.

## Decision
We chose the **Inbox and Outbox Transactional Patterns**.

## Consequences & Rationale
- **Reliable Publishing**: The Outbox pattern writes event payloads to `outbox_events` table in the database transaction. Background workers poll and publish events to Kafka, guaranteeing delivery.
- **Idempotency (Exactly-Once Semantics)**: The Inbox pattern records received event IDs in the consumer database. Retried or duplicated Kafka messages are checked against the Inbox list and discarded if already processed.
- **Eventual Consistency**: Reconciles dual-write inconsistencies with zero cross-database locking.
