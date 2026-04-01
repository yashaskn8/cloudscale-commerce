# Architectural Decision Record — ADR-001: FastAPI for Service Layer

## Context & Problem
We require a high-throughput, low-latency, asynchronous framework for the Python microservices. The framework must support static type checking, automated OpenAPI schema generation, and dependency injection.

## Options Considered
1. **Flask**: Lightweight but lacks native async support and out-of-the-box OpenAPI capabilities.
2. **Django / Django Ninja**: Robust but carries high framework overhead and is less suited for lightweight distributed services.
3. **FastAPI**: Asynchronous-first ASGI framework built on top of Starlette and Pydantic.

## Decision
We chose **FastAPI** as the standard application layer framework.

## Consequences & Rationale
- **Performance**: High performance on par with NodeJS and Go due to ASGI runtime support.
- **Developer Velocity**: Automatic interactive Swagger UI docs based on Pydantic schemas.
- **Type Safety**: Native type-hint parsing blocks malformed payloads at the edge.
- **Dependency Injection**: Streamlines mock overrides for unit and database testing.
