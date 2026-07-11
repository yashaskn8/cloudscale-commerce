"""Notification Service — Domain Models.

Defines the transactional Inbox table for exactly-once notification delivery.
"""

from cloudscale_shared.inbox import InboxMixin
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class InboxMessage(Base, InboxMixin):
    """Transactional inbox for Notification Service event deduplication."""

    __tablename__ = "inbox_messages"
