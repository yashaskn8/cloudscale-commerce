"""Inventory Service — Domain Models.

Defines the Inventory aggregate and transactional Outbox/Inbox tables.
"""

import uuid

from cloudscale_shared.inbox import InboxMixin
from cloudscale_shared.outbox import OutboxMixin
from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Inventory(Base):
    __tablename__ = "inventory"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    available_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class OutboxMessage(Base, OutboxMixin):
    """Transactional outbox for Inventory Service events."""

    __tablename__ = "outbox_messages"


class InboxMessage(Base, InboxMixin):
    """Transactional inbox for Inventory Service event deduplication."""

    __tablename__ = "inbox_messages"
