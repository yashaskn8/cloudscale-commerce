import uuid
from decimal import Decimal
from pydantic import BaseModel, Field

class ProductCreate(BaseModel):
    sku: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(..., gt=0)

class ProductResponse(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    description: str | None
    price: Decimal
    is_active: bool

    class Config:
        from_attributes = True
