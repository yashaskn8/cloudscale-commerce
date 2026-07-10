import uuid
from decimal import Decimal
from sqlalchemy import String, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    sku: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(1000), 
        nullable=True
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), 
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(), 
        default=True
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100),
        default="default-tenant",
        nullable=False,
        index=True
    )
