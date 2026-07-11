"""Order Service — Domain Models.

Defines the Order aggregate root, OrderItem value objects, and the
transactional Outbox/Inbox tables for reliable event-driven messaging.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from cloudscale_shared.inbox import InboxMixin
from cloudscale_shared.outbox import OutboxMixin
from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OrderStatus(str, enum.Enum):
    """Saga state machine for order lifecycle."""

    PENDING = "PENDING"
    STOCK_RESERVED = "STOCK_RESERVED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    CANCELLED_NO_STOCK = "CANCELLED_NO_STOCK"
    CANCELLING = "CANCELLING"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=OrderStatus.PENDING.value, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")


class OutboxMessage(Base, OutboxMixin):
    """Transactional outbox for Order Service events."""

    __tablename__ = "outbox_messages"


class InboxMessage(Base, InboxMixin):
    """Transactional inbox for Order Service event deduplication."""

    __tablename__ = "inbox_messages"
