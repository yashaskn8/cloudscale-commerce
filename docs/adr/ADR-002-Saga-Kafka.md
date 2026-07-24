# Architectural Decision Record — ADR-002: Choreographed Sagas via Kafka

## Context & Problem
In a distributed e-commerce platform, checkout spans across Order, Inventory, and Payment services. Traditional two-phase commits (2PC) introduce blocking latency, single points of failure, and lock contention.

## Options Considered
1. **Two-Phase Commit (2PC)**: Tight database coupling with low scalability.
2. **Orchestrated Saga**: Centralized saga coordinator service directing execution. Introduces a single point of failure and higher API routing overhead.
3. **Choreographed Saga**: Distributed asynchronous state machines communicating via Kafka topics.

## Decision
We chose **Choreographed Sagas using Apache Kafka** as the event backbone.

## Consequences & Rationale
- **Decoupling**: Services listen to events, execute localized transactions, and publish results without knowing about downstream consumers.
- **Scalability**: High-throughput Kafka topics handle massive transaction volume without lock waits.
- **Fault Tolerance**: If a service (e.g. Payment) is briefly unreachable, Kafka partition queues buffer messages until the consumer recovers.
- **Compensating Transactions**: Explicit rollback events (e.g. `PaymentFailedEvent` triggers stock release) maintain eventual consistency.
