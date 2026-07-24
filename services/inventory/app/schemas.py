import uuid

from pydantic import BaseModel, ConfigDict, Field


class RestockRequest(BaseModel):
    quantity: int = Field(..., gt=0)


class InventoryResponse(BaseModel):
    product_id: uuid.UUID
    available_stock: int
    reserved_stock: int

    model_config = ConfigDict(from_attributes=True)
