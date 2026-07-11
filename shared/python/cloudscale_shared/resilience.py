"""Production-Grade Resiliency Framework.

Provides:
- Circuit Breaker pattern with state transition monitoring
- Retry with Exponential Backoff and Jitter
- Bulkhead Isolation using async semaphores
- Timeout policy context managers
- Prometheus metrics monitoring for retries, breaker states, and bulkhead usage
"""

import asyncio
import time
from collections.abc import Callable, Coroutine
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

import structlog
from prometheus_client import Counter, Gauge
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = structlog.get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# Prometheus Resiliency Metrics
# ──────────────────────────────────────────────────────────────────────────────

RETRY_COUNT = Counter("resiliency_retries_total", "Total number of operation retry attempts", ["operation"])

CIRCUIT_BREAKER_STATE = Gauge(
    "resiliency_circuit_breaker_state", "State of the circuit breaker (0=closed, 1=open, 2=half-open)", ["operation"]
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "resiliency_circuit_breaker_failures_total", "Total failure counts registered by circuit breakers", ["operation"]
)

BULKHEAD_UTILIZATION = Gauge(
    "resiliency_bulkhead_active_requests", "Active concurrent requests within a bulkhead slot", ["operation"]
)

BULKHEAD_LIMITS = Gauge("resiliency_bulkhead_limit", "Limit configuration of the bulkhead semaphore", ["operation"])


# ──────────────────────────────────────────────────────────────────────────────
# 1. Retry Policy with Exponential Backoff
# ──────────────────────────────────────────────────────────────────────────────

T = TypeVar("T")


def retry_with_backoff(
    operation_name: str,
    max_attempts: int = 3,
    min_backoff_seconds: float = 0.5,
    max_backoff_seconds: float = 4.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator applying exponential backoff retry with random jitter."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            def before_sleep_cb(retry_state: Any) -> None:
                RETRY_COUNT.labels(operation=operation_name).inc()
                logger.warn(
                    "Retrying operation after failure",
                    operation=operation_name,
                    attempt=retry_state.attempt_number,
                    idle_seconds=retry_state.next_action.sleep,
                )

            # Define tenacity retry strategy
            tenacity_retry = retry(
                reraise=True,
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential_jitter(initial=min_backoff_seconds, max=max_backoff_seconds, exp_base=2),
                retry=retry_if_exception_type(retry_exceptions),
                before_sleep=before_sleep_cb,
            )
            return tenacity_retry(func)(*args, **kwargs)

        return wrapper

    return decorator


# ──────────────────────────────────────────────────────────────────────────────
# 2. Circuit Breaker Pattern
# ──────────────────────────────────────────────────────────────────────────────


class CircuitState(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class CircuitBreakerOpenException(Exception):
    """Exception raised when a circuit breaker is in OPEN state."""

    pass


class CircuitBreaker:
    """Tracks failure state and controls execution flow to external resources."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()

        CIRCUIT_BREAKER_STATE.labels(operation=name).set(CircuitState.CLOSED.value)

    def transition_to(self, new_state: CircuitState) -> None:
        """Transitions state and records metrics."""
        self.state = new_state
        self.last_state_change = time.time()
        CIRCUIT_BREAKER_STATE.labels(operation=self.name).set(new_state.value)
        logger.info(
            "Circuit breaker state transitioned",
            breaker=self.name,
            state=new_state.name,
        )

    def record_success(self) -> None:
        """Resets counters on successful operation call."""
        self.failure_count = 0
        if self.state != CircuitState.CLOSED:
            self.transition_to(CircuitState.CLOSED)

    def record_failure(self) -> None:
        """Increments failures and triggers transition to OPEN if threshold met."""
        self.failure_count += 1
        CIRCUIT_BREAKER_FAILURES.labels(operation=self.name).inc()
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self.transition_to(CircuitState.OPEN)

    def check_state(self) -> None:
        """Verifies state timeout and transitions OPEN -> HALF-OPEN if ready."""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_state_change
            if elapsed >= self.recovery_timeout_seconds:
                self.transition_to(CircuitState.HALF_OPEN)


def circuit_breaker(
    breaker: CircuitBreaker,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Decorator wrapping an async call inside a Circuit Breaker pattern."""

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            breaker.check_state()
            if breaker.state == CircuitState.OPEN:
                raise CircuitBreakerOpenException(f"Circuit breaker {breaker.name} is open. Request rejected.")

            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception:
                breaker.record_failure()
                raise

        return wrapper

    return decorator


# ──────────────────────────────────────────────────────────────────────────────
# 3. Bulkhead Isolation Pattern
# ──────────────────────────────────────────────────────────────────────────────


class BulkheadLimitExceeded(Exception):
    """Exception raised when bulkhead maximum capacity is exceeded."""

    pass


class Bulkhead:
    """Controls execution concurrency using async semaphores."""

    def __init__(self, name: str, max_concurrent: int):
        self.name = name
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

        BULKHEAD_LIMITS.labels(operation=name).set(max_concurrent)

    async def execute(self, coro: Coroutine[Any, Any, T]) -> T:
        """Executes a coroutine checking bulkhead capacity."""
        if self.semaphore.locked():
            logger.warn("Bulkhead limit reached", bulkhead=self.name)
            raise BulkheadLimitExceeded(f"Bulkhead {self.name} reached limit capacity of {self.max_concurrent}")

        BULKHEAD_UTILIZATION.labels(operation=self.name).inc()
        try:
            async with self.semaphore:
                return await coro
        finally:
            BULKHEAD_UTILIZATION.labels(operation=self.name).dec()


def bulkhead(
    bulkhead_obj: Bulkhead,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Decorator executing an async function within a bulkhead boundary."""

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await bulkhead_obj.execute(func(*args, **kwargs))

        return wrapper

    return decorator


# ──────────────────────────────────────────────────────────────────────────────
# 4. Timeout Policies
# ──────────────────────────────────────────────────────────────────────────────


def with_timeout(
    seconds: float,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Decorator enforcing maximum runtime limit on an async operation."""

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except TimeoutError:
                logger.error(
                    "Operation timed out",
                    func=func.__name__,
                    timeout_seconds=seconds,
                )
                raise TimeoutError(f"Operation timed out after {seconds} seconds.")

        return wrapper

    return decorator
