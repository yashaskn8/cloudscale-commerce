# CloudScale Commerce — System Architecture & C4 Model Diagrams

This document contains Mermaid diagrams visualizing the platform's distributed container topology, checkout saga state machines, and relational schemas.

---

## 1. C4 Context Diagram
The high-level boundary of the e-commerce system, its actors, and external system integrations.

```mermaid
graph TD
    User["Customer (Web/Mobile App)"]
    Admin["Merchant / Store Admin"]
    System["CloudScale Platform (FastAPI / K8s)"]
    Gateway["Stripe (Payment Gateway)"]
    SMTP["AWS SES (Email Service)"]

    User -->|"Browses catalog, places orders"| System
    Admin -->|"Manages catalog, updates stock"| System
    System -->|"Processes card transactions"| Gateway
    System -->|"Dispatches email alerts"| SMTP
```

---

## 2. C4 Container Diagram
Details the microservice boundaries, databases, caches, and communication protocols.

```mermaid
graph TB
    subgraph Edge
        Ingress["Kong Ingress Controller (Port 443 / SSL)"]
    end

    subgraph Service Layer
        Auth["Auth Service (Port 8001)"]
        Catalog["Catalog Service (Port 8002)"]
        Inventory["Inventory Service (Port 8003)"]
        Order["Order Service (Port 8004)"]
        Payment["Payment Service (Port 8005)"]
        Notification["Notification Service (Port 8006)"]
    end

    subgraph Datastores & Queues
        Postgres[("PostgreSQL 15 (DB Per Service)")]
        Redis[("Redis 7 (L2 Cache + Locks)")]
        Kafka{{"Apache Kafka (Event Bus)"}}
    end

    Ingress -->|"/api/v1/auth"| Auth
    Ingress -->|"/api/v1/products"| Catalog
    Ingress -->|"/api/v1/orders"| Order

    Auth --> Redis
    Auth --> Postgres
    
    Catalog --> Redis
    Catalog --> Postgres

    Order --> Postgres
    Order --> Kafka

    Inventory --> Postgres
    Inventory --> Kafka
    
    Payment --> Kafka
    Notification --> Kafka
```

---

## 3. Sequence Diagram — Order Checkout Saga Flow
Detailed message sequence demonstrating the choreographed Saga pattern coordinating transactions across services.

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant OrderService
    participant Kafka
    participant InventoryService
    participant PaymentService

    Customer->>OrderService: POST /api/v1/orders (Place Order)
    OrderService->>OrderService: Write Order (PENDING) & Outbox Event
    OrderService-->>Customer: 201 Created (Order Pending)
    
    OrderService->>Kafka: Publish "OrderCreatedEvent"
    Kafka->>InventoryService: Consume "OrderCreatedEvent"
    
    alt Stock Available
        InventoryService->>InventoryService: Reserve Stock
        InventoryService->>Kafka: Publish "InventoryReservedEvent"
        Kafka->>PaymentService: Consume "InventoryReservedEvent"
        
        alt Payment Successful
            PaymentService->>PaymentService: Charge Card
            PaymentService->>Kafka: Publish "PaymentCompletedEvent"
            Kafka->>OrderService: Consume "PaymentCompletedEvent"
            OrderService->>OrderService: Update Order (SUCCESS)
        else Payment Failed
            PaymentService->>Kafka: Publish "PaymentFailedEvent"
            Kafka->>InventoryService: Consume "PaymentFailedEvent" (Compensating Transaction)
            InventoryService->>InventoryService: Release Reserved Stock
            Kafka->>OrderService: Consume "PaymentFailedEvent"
            OrderService->>OrderService: Update Order (CANCELLED)
        end
        
    else Out of Stock
        InventoryService->>Kafka: Publish "InventoryReservationFailedEvent"
        Kafka->>OrderService: Consume "InventoryReservationFailedEvent"
        OrderService->>OrderService: Update Order (FAILED)
    end
```

---

## 4. Database ER Schema (Shared Topologies)
Entities and relationships mapped within each database schema boundaries.

```mermaid
erDiagram
    USERS {
        uuid id PK
        string email
        string password_hash
        string role
        boolean is_active
    }
    PRODUCTS {
        uuid id PK
        string sku
        string name
        decimal price
        boolean is_active
    }
    INVENTORY {
        uuid id PK
        string sku
        int quantity
        int reserved
    }
    ORDERS {
        uuid id PK
        uuid user_id
        string status
        decimal total_amount
    }
    ORDER_ITEMS {
        uuid id PK
        uuid order_id FK
        uuid product_id
        int quantity
        decimal price
    }

    ORDERS ||--o{ ORDER_ITEMS : contains
```
