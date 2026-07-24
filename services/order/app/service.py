"""Order Service — Business Service Layer.

Coordinates Order aggregates, validates checkout commands, implements idempotency,
and writes Saga initiation events to the transactional outbox (not directly to Kafka).
"""

import uuid
from datetime import datetime

import structlog
from app.config import settings
from app.models import Order, OrderItem, OrderStatus, OutboxMessage
from app.repository import OrderRepository
from app.schemas import OrderAnalyticsResponse, OrderCreate
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
        # 6. Write OrderCreatedEvent to outbox within the same local transaction
        event = Event(
            event_type="OrderCreatedEvent",
            aggregate_id=str(new_order.id),
            correlation_id=correlation_id,
            payload=event_payload,
        )
        write_outbox(
            self.session,
            OutboxMessage,
            settings.ORDER_EVENTS_TOPIC,
            event,
            key=str(new_order.id),
        )

        # 7. Low-cardinality Prometheus telemetry
        from app.metrics import ORDERS_CREATED, ORDERS_REVENUE_TOTAL

        ORDERS_CREATED.labels(service="order-service").inc()
        ORDERS_REVENUE_TOTAL.inc(float(total_amount))

        logger.info(
            "Order created & Outbox event written",
            order_id=str(new_order.id),
            correlation_id=correlation_id,
        )
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

    async def get_analytics(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        status_filter: str | None = None,
        top_n: int = 10,
    ) -> OrderAnalyticsResponse:
        """Computes Read Committed near-real-time order analytics directly via PostgreSQL aggregate queries."""
        from datetime import datetime
        from decimal import Decimal

        from app.schemas import OrderAnalyticsResponse, TopSellingItem
        from sqlalchemy import func, select

        tenant_id = get_current_tenant()

        # Query 1: Total orders, total revenue, average order value
        stmt = select(
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.0")).label("total_revenue"),
            func.coalesce(func.avg(Order.total_amount), Decimal("0.0")).label("average_order_value"),
        ).where(Order.tenant_id == tenant_id)

        if from_date:
            stmt = stmt.where(Order.created_at >= from_date)
        if to_date:
            stmt = stmt.where(Order.created_at <= to_date)
        if status_filter:
            stmt = stmt.where(Order.status == status_filter)

        res = await self.session.execute(stmt)
        row = res.one()

        total_orders = int(row.total_orders or 0)
        total_revenue = Decimal(str(row.total_revenue or "0.0"))
        avg_order_val = Decimal(str(row.average_order_value or "0.0"))

        # Query 2: Status Breakdown
        status_stmt = (
            select(Order.status, func.count(Order.id)).where(Order.tenant_id == tenant_id).group_by(Order.status)
        )
        if from_date:
            status_stmt = status_stmt.where(Order.created_at >= from_date)
        if to_date:
            status_stmt = status_stmt.where(Order.created_at <= to_date)

        status_res = await self.session.execute(status_stmt)
        status_breakdown: dict[str, int] = {str(r[0]): int(r[1]) for r in status_res.all()}

        # Query 3: Top Selling Items
        top_items_stmt = (
            select(OrderItem.product_id, func.sum(OrderItem.quantity).label("total_qty"))
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.tenant_id == tenant_id)
            .group_by(OrderItem.product_id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(min(top_n, 100))
        )
        if from_date:
            top_items_stmt = top_items_stmt.where(Order.created_at >= from_date)
        if to_date:
            top_items_stmt = top_items_stmt.where(Order.created_at <= to_date)

        top_res = await self.session.execute(top_items_stmt)
        top_selling_items = [
            TopSellingItem(product_id=pid, total_quantity_sold=int(qty or 0)) for pid, qty in top_res.all()
        ]

        return OrderAnalyticsResponse(
            total_orders=total_orders,
            total_revenue=total_revenue,
            average_order_value=avg_order_val,
            status_breakdown=status_breakdown,
            top_selling_items=top_selling_items,
        )
