"""Payment Service — Domain Models.

Defines the Payment transaction record, Subscription models, Plans, Invoices, and transactional Outbox/Inbox tables.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, DateTime, func, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from cloudscale_shared.outbox import OutboxMixin
from cloudscale_shared.inbox import InboxMixin


class Base(DeclarativeBase):
    pass


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    plan_tier: Mapped[str] = mapped_column(String(50), default="free", nullable=False) # free, growth, enterprise
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False) # active, past_due, cancelled
    current_period_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="paid", nullable=False) # paid, pending, failed
    billing_date: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class OutboxMessage(Base, OutboxMixin):
    """Transactional outbox for Payment Service events."""
    __tablename__ = "outbox_messages"


class InboxMessage(Base, InboxMixin):
    """Transactional inbox for Payment Service event deduplication."""
    __tablename__ = "inbox_messages"
