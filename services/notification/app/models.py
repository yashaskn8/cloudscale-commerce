"""Notification Service — Domain Models.

Defines the transactional Inbox table for exactly-once notification delivery.
"""
from sqlalchemy.orm import DeclarativeBase
from cloudscale_shared.inbox import InboxMixin


class Base(DeclarativeBase):
    pass


class InboxMessage(Base, InboxMixin):
    """Transactional inbox for Notification Service event deduplication."""
    __tablename__ = "inbox_messages"
