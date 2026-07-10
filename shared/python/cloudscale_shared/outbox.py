"""Transactional Outbox Pattern.

Provides the `OutboxMessage` SQLAlchemy model mixin and `OutboxWorker` background
task. Services write events to the outbox table within the same DB transaction as
their domain changes. The worker polls the table, publishes to Kafka, and marks
records as processed — guaranteeing at-least-once delivery without coupling DB
transactions to Kafka availability.

Usage in a service's models.py:
    from cloudscale_shared.outbox import OutboxMixin
    class OutboxMessage(Base, OutboxMixin):
        __tablename__ = "outbox_messages"
"""
import asyncio
import json
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from cloudscale_shared.events import Event, KafkaProducerWrapper

logger = structlog.get_logger()


class OutboxMixin:
    """Mixin providing outbox message columns. Inherit alongside your Base."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


def write_outbox(
    session: AsyncSession,
    outbox_model: type,
    topic: str,
    event: Event,
    key: str | None = None,
) -> None:
    """Writes an event record to the outbox table within the current transaction.

    Args:
        session: The active SQLAlchemy async session (must be within a transaction).
        outbox_model: The concrete OutboxMessage ORM class for this service.
        topic: Kafka topic name.
        event: The domain event to publish.
        key: Optional Kafka partition key.
    """
    record = outbox_model(
        event_id=event.event_id,
        event_type=event.event_type,
        topic=topic,
        key=key,
        payload=json.dumps(event.model_dump()),
        correlation_id=event.correlation_id,
    )
    session.add(record)
    logger.debug(
        "Outbox record written",
        event_type=event.event_type,
        event_id=event.event_id,
        topic=topic,
    )


class OutboxWorker:
    """Background worker that polls the outbox table and publishes to Kafka.

    Runs as an asyncio task within the service's lifespan. Processes unpublished
    messages in batches, retrying failures up to `max_retries` before logging
    and skipping permanently failed records.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        outbox_model: type,
        producer: KafkaProducerWrapper,
        poll_interval_seconds: float = 1.0,
        batch_size: int = 50,
        max_retries: int = 5,
    ):
        self.sessionmaker = sessionmaker
        self.outbox_model = outbox_model
        self.producer = producer
        self.poll_interval = poll_interval_seconds
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._running = False

    async def start(self) -> None:
        """Starts the outbox polling loop as a background task."""
        self._running = True
        asyncio.create_task(self._poll_loop())
        logger.info("Outbox worker started.")

    async def stop(self) -> None:
        """Signals the polling loop to stop."""
        self._running = False
        logger.info("Outbox worker stopped.")

    async def _poll_loop(self) -> None:
        """Continuously polls the outbox table for unpublished messages."""
        while self._running:
            try:
                await self._process_batch()
            except Exception as exc:
                logger.error("Outbox worker poll error", error=str(exc))
            await asyncio.sleep(self.poll_interval)

    async def _process_batch(self) -> None:
        """Fetches and publishes a batch of unprocessed outbox records."""
        async with self.sessionmaker() as session:
            stmt = (
                select(self.outbox_model)
                .where(
                    self.outbox_model.processed == False,
                    self.outbox_model.retry_count < self.max_retries,
                )
                .order_by(self.outbox_model.created_at.asc())
                .limit(self.batch_size)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

            for record in records:
                try:
                    event_data = json.loads(record.payload)
                    event = Event(**event_data)
                    await self.producer.send_event(
                        record.topic, event, key=record.key
                    )
                    record.processed = True
                    logger.info(
                        "Outbox message published",
                        event_id=record.event_id,
                        topic=record.topic,
                    )
                except Exception as exc:
                    record.retry_count += 1
                    logger.error(
                        "Failed to publish outbox message",
                        event_id=record.event_id,
                        retry_count=record.retry_count,
                        error=str(exc),
                    )

            await session.commit()
