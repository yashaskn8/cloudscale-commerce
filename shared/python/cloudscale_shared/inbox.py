"""Transactional Inbox Pattern.

Provides the `InboxMixin` SQLAlchemy model mixin and an `inbox_guard` helper.
Consuming services check the inbox table before processing an event. If the
event_id already exists, it is skipped — guaranteeing exactly-once processing
semantics at the application layer.

Usage in a service's models.py:
    from cloudscale_shared.inbox import InboxMixin
    class InboxMessage(Base, InboxMixin):
        __tablename__ = "inbox_messages"
"""
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import String, DateTime, select, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

logger = structlog.get_logger()


class InboxMixin:
    """Mixin providing inbox deduplication columns. Inherit alongside your Base."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    source_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


async def inbox_already_processed(
    session: AsyncSession,
    inbox_model: type,
    event_id: str,
) -> bool:
    """Checks if an event has already been processed (exists in inbox table).

    Args:
        session: Active SQLAlchemy async session.
        inbox_model: The concrete InboxMessage ORM class for this service.
        event_id: The unique event identifier to check.

    Returns:
        True if the event was already processed, False otherwise.
    """
    stmt = select(func.count()).select_from(inbox_model).where(
        inbox_model.event_id == event_id
    )
    result = await session.execute(stmt)
    count = result.scalar_one()
    if count > 0:
        logger.info("Duplicate event detected in inbox, skipping", event_id=event_id)
        return True
    return False


def record_inbox(
    session: AsyncSession,
    inbox_model: type,
    event_id: str,
    event_type: str,
    source_topic: str,
) -> None:
    """Records an event in the inbox table to prevent future duplicate processing.

    Args:
        session: Active SQLAlchemy async session (must be within a transaction).
        inbox_model: The concrete InboxMessage ORM class for this service.
        event_id: The unique event identifier.
        event_type: The type/name of the event.
        source_topic: The Kafka topic the event was consumed from.
    """
    record = inbox_model(
        event_id=event_id,
        event_type=event_type,
        source_topic=source_topic,
    )
    session.add(record)
    logger.debug("Inbox record written", event_id=event_id, event_type=event_type)
