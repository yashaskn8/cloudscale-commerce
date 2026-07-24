"""Order Service — Business Service Layer.

Coordinates Order aggregates, validates checkout commands, implements idempotency,
and writes Saga initiation events to the transactional outbox (not directly to Kafka).
"""

import uuid

import structlog
from app.config import settings
from app.models import Order, OrderItem, OrderStatus, OutboxMessage
from app.repository import OrderRepository
from app.schemas import OrderCreate
from cloudscale_shared import NotFoundException, ValidationException, get_current_tenant
from cloudscale_shared.events import Event
from cloudscale_shared.outbox import write_outbox
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class OrderService:
    """Service layer handling order transactions and Saga initiation via outbox."""

    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.repo = OrderRepository(session)
        self.session = session
        self.redis = redis

    async def get_order(self, order_id: uuid.UUID) -> Order:
        """Retrieves an order by its unique primary key and verifies tenant context."""
        order = await self.repo.get_by_id(order_id)
        if not order or order.tenant_id != get_current_tenant():
            raise NotFoundException("Order not found")
        return order

    async def create_order(self, user_uuid: uuid.UUID, payload: OrderCreate) -> Order:
        """Saves a new order with tenant quota checks, and writes an OrderCreatedEvent to outbox."""
        tenant_id = get_current_tenant()

        max_limit = 15
        if self.redis:
            # Resolve active subscription limits from Redis plan context
            plan_raw = await self.redis.get(f"tenant:plan:{tenant_id}")
            plan_tier = plan_raw.decode() if isinstance(plan_raw, bytes) else (plan_raw or "free")
            limits: dict[str, int] = {"free": 15, "growth": 200, "enterprise": 20000}
            max_limit = limits.get(plan_tier, 15)

            current_count = await self.repo.count_tenant_orders()
            if current_count >= max_limit:
                logger.warn("Order checkout failed - Quota limit exceeded", tenant_id=tenant_id, plan_tier=plan_tier)
                raise ValidationException(
                    f"Order checkout quota limit of {max_limit} exceeded for plan '{plan_tier}'. Please upgrade."
                )

        # 1. Idempotency Check
        existing_order = await self.repo.get_by_idempotency_key(payload.idempotency_key)
        if existing_order:
            logger.info(
                "Duplicate request detected. Returning existing order.",
                idempotency_key=payload.idempotency_key,
                order_id=str(existing_order.id),
            )
            return existing_order

        # 2. Compute total amount
        total_amount = sum(item.quantity * item.unit_price for item in payload.items)

        # 3. Create order in PENDING status
        new_order = Order(
            user_id=user_uuid,
            status=OrderStatus.PENDING.value,
            total_amount=total_amount,
            idempotency_key=payload.idempotency_key,
            tenant_id=tenant_id,
        )
        await self.repo.add(new_order)
        await self.session.flush()

        # 4. Save nested items
        for item in payload.items:
            new_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            self.session.add(new_item)

        # 5. Build OrderCreatedEvent
        correlation_id = structlog.contextvars.get_contextvars().get("correlation_id", str(uuid.uuid4()))
        event_payload = {
            "order_id": str(new_order.id),
            "user_id": str(user_uuid),
            "total_amount": float(total_amount),
            "items": [
                {
                    "product_id": str(i.product_id),
                    "quantity": i.quantity,
                    "unit_price": float(i.unit_price),
                }
                for i in payload.items
            ],
        }
        event = Event(
            event_type="OrderCreatedEvent",
            correlation_id=correlation_id,
            payload=event_payload,
        )

        # 6. Write event to outbox (same transaction as order insert)
        write_outbox(
            self.session,
            OutboxMessage,
            settings.ORDER_EVENTS_TOPIC,
            event,
            key=str(new_order.id),
        )

        await self.session.flush()
        logger.info("Order saved with outbox event", order_id=str(new_order.id))

        return new_order

    async def transition_status(self, order_id: str, new_status: OrderStatus, correlation_id: str) -> Order | None:
        """Transitions an order to a new Saga state, writing audit log."""
        order = await self.repo.get_by_id(uuid.UUID(order_id))
        if not order:
            logger.error("Order not found for state transition", order_id=order_id)
            return None

        old_status = order.status
        order.status = new_status.value
        await self.session.flush()

        logger.info(
            "Order status transitioned",
            order_id=order_id,
            old_status=old_status,
            new_status=new_status.value,
            correlation_id=correlation_id,
        )
        return order
