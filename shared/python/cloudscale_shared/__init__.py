from cloudscale_shared.logging import setup_logging
from cloudscale_shared.middleware import CorrelationIdMiddleware, TenantContextMiddleware, get_current_tenant
from cloudscale_shared.database import (
    init_db,
    init_redis,
    get_db_session,
    get_read_db_session,
    get_redis_client,
    DatabaseSessionManager,
    RedisManager,
    cursor_paginate
)
from cloudscale_shared.events import (
    Event,
    KafkaProducerWrapper,
    KafkaConsumerWrapper
)
from cloudscale_shared.exceptions import (
    CloudScaleException,
    NotFoundException,
    ConflictException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    setup_exception_handlers
)
from cloudscale_shared.repository import (
    AbstractRepository,
    SQLAlchemyRepository
)
from cloudscale_shared.uow import (
    AbstractUnitOfWork,
    SQLAlchemyUnitOfWork
)
from cloudscale_shared.query import (
    PageParams,
    Page
)
from cloudscale_shared.metrics import (
    setup_metrics,
    register_health_routes
)
from cloudscale_shared.tracing import (
    setup_tracing,
    inject_trace_into_event,
    extract_trace_from_event,
    get_current_ids
)
from cloudscale_shared.outbox import (
    OutboxMixin,
    write_outbox,
    OutboxWorker
)
from cloudscale_shared.inbox import (
    InboxMixin,
    inbox_already_processed,
    record_inbox
)
from cloudscale_shared.security import (
    hash_password,
    verify_password,
    password_needs_rehash,
    validate_password_policy,
    create_token_pair,
    decode_token,
    revoke_token,
    is_token_revoked,
    record_failed_login,
    is_account_locked,
    clear_failed_logins,
    RoleChecker,
    RateLimiter,
    SecurityHeadersMiddleware,
    audit_log,
)

__all__ = [
    "setup_logging",
    "CorrelationIdMiddleware",
    "TenantContextMiddleware",
    "get_current_tenant",
    "init_db",
    "init_redis",
    "get_db_session",
    "get_read_db_session",
    "get_redis_client",
    "DatabaseSessionManager",
    "RedisManager",
    "cursor_paginate",
    "Event",
    "KafkaProducerWrapper",
    "KafkaConsumerWrapper",
    "CloudScaleException",
    "NotFoundException",
    "ConflictException",
    "UnauthorizedException",
    "ForbiddenException",
    "ValidationException",
    "setup_exception_handlers",
    "AbstractRepository",
    "SQLAlchemyRepository",
    "AbstractUnitOfWork",
    "SQLAlchemyUnitOfWork",
    "PageParams",
    "Page",
    "setup_metrics",
    "OutboxMixin",
    "write_outbox",
    "OutboxWorker",
    "InboxMixin",
    "inbox_already_processed",
    "record_inbox",
    "hash_password",
    "verify_password",
    "password_needs_rehash",
    "validate_password_policy",
    "create_token_pair",
    "decode_token",
    "revoke_token",
    "is_token_revoked",
    "record_failed_login",
    "is_account_locked",
    "clear_failed_logins",
    "RoleChecker",
    "RateLimiter",
    "SecurityHeadersMiddleware",
    "audit_log",
    "retry_with_backoff",
    "circuit_breaker",
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpenException",
    "bulkhead",
    "Bulkhead",
    "BulkheadLimitExceeded",
    "with_timeout",
    "cache_aside",
    "invalidate_cache_key",
]

from cloudscale_shared.resilience import (
    retry_with_backoff,
    circuit_breaker,
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenException,
    bulkhead,
    Bulkhead,
    BulkheadLimitExceeded,
    with_timeout,
)
from cloudscale_shared.cache import (
    cache_aside,
    invalidate_cache_key,
)
