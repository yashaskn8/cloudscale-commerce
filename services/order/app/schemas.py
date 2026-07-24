import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(..., min_length=1)
    idempotency_key: str = Field(..., min_length=10)


class OrderItemResponse(BaseModel):
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    total_amount: Decimal
    created_at: datetime
    items: list[OrderItemResponse]

    model_config = ConfigDict(from_attributes=True)


class TopSellingItem(BaseModel):
    product_id: uuid.UUID
    total_quantity_sold: int


class OrderAnalyticsResponse(BaseModel):
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    status_breakdown: dict[str, int]
    top_selling_items: list[TopSellingItem]
