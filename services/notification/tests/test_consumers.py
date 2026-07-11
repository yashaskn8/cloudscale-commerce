import uuid

import pytest
from app.consumers import handle_event
from app.models import InboxMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_notification_delivery_and_deduplication(db_session: AsyncSession, monkeypatch):
    from unittest.mock import AsyncMock

    # Mock order confirmation method
    mock_send = AsyncMock()
    monkeypatch.setattr("app.consumers.send_order_confirmation", mock_send)

    order_id = uuid.uuid4()
    correlation_id = "test-corr-notification"
    event_id = str(uuid.uuid4())

    # Simulate PaymentSuccessEvent
    payment_success_event = {
        "event_id": event_id,
        "event_type": "PaymentSuccessEvent",
        "correlation_id": correlation_id,
        "payload": {"order_id": str(order_id), "transaction_id": "txn_notif_123"},
    }

    # 1. First execution
    await handle_event(payment_success_event)
    await db_session.commit()

    assert mock_send.call_count == 1
    mock_send.assert_called_with(payment_success_event["payload"], correlation_id)

    # Verify inbox entry is logged
    inbox_stmt = select(InboxMessage).where(InboxMessage.event_id == event_id)
    inbox_res = await db_session.execute(inbox_stmt)
    inbox = inbox_res.scalars().all()
    assert len(inbox) == 1

    # 2. Second execution (Duplicate message delivery check)
    await handle_event(payment_success_event)
    await db_session.commit()

    # Call count must still be 1 (second call was skipped by inbox deduplication)
    assert mock_send.call_count == 1
