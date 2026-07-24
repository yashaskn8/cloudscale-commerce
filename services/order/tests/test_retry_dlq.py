from unittest.mock import AsyncMock

import pytest
from cloudscale_shared.events import KafkaConsumerWrapper


@pytest.mark.asyncio
async def test_consumer_retry_and_dlq(monkeypatch):
    # Create wrapper
    wrapper = KafkaConsumerWrapper(
        bootstrap_servers="localhost:9092", group_id="test-group", topics=["order-events"], max_retries=2
    )

    # Mock the internal retry/DLQ producer
    mock_producer = AsyncMock()
    wrapper._retry_producer = mock_producer

    # Create mock message structure
    class MockMessage:
        def __init__(self):
            self.topic = "order-events"
            self.partition = 0
            self.offset = 100
            self.key = b"order-123"
            self.value = {
                "event_id": "evt-123",
                "event_type": "OrderCreatedEvent",
                "correlation_id": "corr-123",
                "payload": {},
                "retry_count": 0,
            }

    msg = MockMessage()

    # 1. First failure scenario (retry_count < max_retries) -> routes to retry topic
    mock_exc = ValueError("Transient database connection issue")
    await wrapper._handle_failure(msg, msg.value, mock_exc)

    assert mock_producer.send_event.call_count == 1
    call_topic, call_event = mock_producer.send_event.call_args[0][0], mock_producer.send_event.call_args[0][1]
    assert call_topic == "order-events-retry"
    assert call_event.retry_count == 1
    assert call_event.correlation_id == "corr-123"

    # Reset mock call history
    mock_producer.send_event.reset_mock()

    # 2. Max retries exceeded scenario (retry_count == max_retries) -> routes to DLQ
    msg.value["retry_count"] = 2
    await wrapper._handle_failure(msg, msg.value, mock_exc)

    assert mock_producer.send_event.call_count == 1
    call_topic, call_event = mock_producer.send_event.call_args[0][0], mock_producer.send_event.call_args[0][1]
    assert call_topic == "order-events-dlq"
    assert call_event.event_type == "DLQMessage"
    assert call_event.payload["error"] == "Transient database connection issue"
    assert call_event.payload["original_topic"] == "order-events"
