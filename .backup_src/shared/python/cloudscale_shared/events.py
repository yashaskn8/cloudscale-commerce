"""Event-Driven Architecture — Kafka Integration Layer.

Provides the Event schema, KafkaProducerWrapper, and KafkaConsumerWrapper with
built-in retry topic routing and Dead Letter Queue (DLQ) support.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import structlog

logger = structlog.get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# Event Schema
# ──────────────────────────────────────────────────────────────────────────────

class Event(BaseModel):
    """Base schema for all domain events across the platform."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    correlation_id: str
    payload: dict[str, Any]
    version: int = 1
    retry_count: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# Kafka Producer
# ──────────────────────────────────────────────────────────────────────────────

class KafkaProducerWrapper:
    """Publishes events to Kafka with standardized serialization and logging."""

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            enable_idempotence=True,
            compression_type="gzip",
            acks="all",
        )

    async def start(self) -> None:
        await self.producer.start()
        logger.info("Kafka Producer started.")

    async def stop(self) -> None:
        await self.producer.stop()
        logger.info("Kafka Producer stopped.")

    async def send_event(
        self, topic: str, event: Event, key: str | None = None
    ) -> None:
        """Sends an event to a Kafka topic, auto-injecting tracing context."""
        try:
            structlog.contextvars.bind_contextvars(
                correlation_id=event.correlation_id
            )
            logger.info(
                "Publishing event to Kafka",
                topic=topic,
                event_type=event.event_type,
                event_id=event.event_id,
            )
            
            value = event.model_dump()
            try:
                from cloudscale_shared.tracing import inject_trace_into_event
                value = inject_trace_into_event(value)
            except ImportError:
                pass

            await self.producer.send_and_wait(
                topic, key=key, value=value
            )
        except Exception as e:
            logger.exception(
                "Failed to publish event to Kafka",
                topic=topic,
                event_type=event.event_type,
                error=str(e),
            )
            raise


# ──────────────────────────────────────────────────────────────────────────────
# Kafka Consumer with Retry + DLQ
# ──────────────────────────────────────────────────────────────────────────────

class KafkaConsumerWrapper:
    """Consumes events from Kafka topics with built-in retry and DLQ routing.

    Retry logic:
        - On handler failure, if retry_count < max_retries, republish to
          `<topic>-retry` with incremented retry_count.
        - On max retries exceeded, route to `<topic>-dlq` with failure metadata.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        max_retries: int = 3,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.max_retries = max_retries
        self.consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        self.is_running = False
        self._retry_producer: KafkaProducerWrapper | None = None

    async def start(self) -> None:
        await self.consumer.start()
        self.is_running = True
        # Lazy-init a dedicated producer for retry/DLQ publishing
        self._retry_producer = KafkaProducerWrapper(self.bootstrap_servers)
        await self._retry_producer.start()
        logger.info(
            "Kafka Consumer started.", topics=self.topics, group_id=self.group_id
        )

    async def stop(self) -> None:
        self.is_running = False
        await self.consumer.stop()
        if self._retry_producer:
            await self._retry_producer.stop()
        logger.info("Kafka Consumer stopped.")

    async def consume_loop(
        self, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Runs the event loop, feeding messages into the handler with retry/DLQ."""
        try:
            async for msg in self.consumer:
                if not self.is_running:
                    break

                event_data = msg.value
                correlation_id = event_data.get("correlation_id", "unknown")
                structlog.contextvars.clear_contextvars()
                structlog.contextvars.bind_contextvars(
                    correlation_id=correlation_id,
                    topic=msg.topic,
                    partition=msg.partition,
                    offset=msg.offset,
                )

                logger.info(
                    "Received event from Kafka",
                    event_type=event_data.get("event_type"),
                )

                try:
                    # Extract OTel trace context
                    context = None
                    try:
                        from cloudscale_shared.tracing import extract_trace_from_event
                        context = extract_trace_from_event(event_data)
                    except ImportError:
                        pass

                    # Execute handler inside active consumer span
                    try:
                        from opentelemetry import trace
                        tracer = trace.get_tracer("cloudscale-consumer")
                        with tracer.start_as_current_span(
                            f"kafka.consume.{msg.topic}",
                            context=context,
                            kind=trace.SpanKind.CONSUMER
                        ) as span:
                            span.set_attribute("messaging.system", "kafka")
                            span.set_attribute("messaging.destination", msg.topic)
                            span.set_attribute("messaging.kafka.partition", msg.partition)
                            span.set_attribute("messaging.kafka.offset", msg.offset)
                            await handler(event_data)
                    except ImportError:
                        await handler(event_data)

                    await self.consumer.commit()
                except Exception as exc:
                    logger.exception(
                        "Error processing event",
                        error=str(exc),
                    )
                    await self._handle_failure(msg, event_data, exc)
                    await self.consumer.commit()
        except Exception as e:
            logger.exception("Kafka consume loop error", error=str(e))
        finally:
            await self.stop()

    async def _handle_failure(
        self, msg: Any, event_data: dict[str, Any], exception: Exception
    ) -> None:
        """Routes failed messages to retry topic or DLQ based on retry count."""
        retry_count = event_data.get("retry_count", 0)

        if retry_count < self.max_retries:
            # Republish to retry topic with incremented count
            retry_topic = f"{msg.topic}-retry"
            event_data["retry_count"] = retry_count + 1
            logger.warn(
                "Routing to retry topic",
                retry_topic=retry_topic,
                attempt=retry_count + 1,
            )
            try:
                retry_event = Event(**{
                    k: v for k, v in event_data.items()
                    if k in Event.model_fields
                })
                await self._retry_producer.send_event(
                    retry_topic, retry_event, key=msg.key.decode("utf-8") if msg.key else None
                )
            except Exception as retry_exc:
                logger.error("Failed to send to retry topic", error=str(retry_exc))
                await self._send_to_dlq(msg, event_data, exception)
        else:
            await self._send_to_dlq(msg, event_data, exception)

    async def _send_to_dlq(
        self, msg: Any, event_data: dict[str, Any], exception: Exception
    ) -> None:
        """Route permanently failed message to Dead Letter Queue topic."""
        dlq_topic = f"{msg.topic}-dlq"
        logger.error(
            "Max retries exceeded. Sending to DLQ.",
            dlq_topic=dlq_topic,
            event_id=event_data.get("event_id"),
        )
        try:
            dlq_payload = {
                "original_topic": msg.topic,
                "original_partition": msg.partition,
                "original_offset": msg.offset,
                "error": str(exception),
                "payload": event_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            dlq_event = Event(
                event_type="DLQMessage",
                correlation_id=event_data.get("correlation_id", "unknown"),
                payload=dlq_payload,
            )
            await self._retry_producer.send_event(
                dlq_topic, dlq_event, key=msg.key.decode("utf-8") if msg.key else None
            )
        except Exception as dlq_exc:
            logger.error(
                "CRITICAL: Failed to send to DLQ", error=str(dlq_exc)
            )
