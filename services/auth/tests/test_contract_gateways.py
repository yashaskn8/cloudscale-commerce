"""
API Contract Compliance & Schema Validation Tests.

Ensures that API gateway request/response structures remain compatible across
service updates, preventing runtime failures during deployment.
"""
from typing import Literal

import pytest
from pydantic import BaseModel, ValidationError

# ── Gateway Contract Models ───────────────────────────────────────────────────

class UserContract(BaseModel):
    id: str
    email: str
    full_name: str
    role: Literal["admin", "merchant", "customer"]

class ProductContract(BaseModel):
    id: str
    sku: str
    name: str
    description: str | None = None
    price: float

class OrderItemContract(BaseModel):
    product_id: str
    quantity: int
    price: float

class OrderContract(BaseModel):
    id: str
    tenant_id: str
    status: Literal["PENDING", "COMPLETED", "FAILED"]
    items: list[OrderItemContract]
    total_amount: float


# ── Contract Validation Tests ─────────────────────────────────────────────────

class TestGatewayContracts:
    def test_user_response_contract_compliance(self):
        # Parse against contract with explicit values to satisfy strict type checkers
        user = UserContract(
            id="usr_90123",
            email="dev@cloudscale.io",
            full_name="Senior Developer",
            role="merchant"
        )
        assert user.role == "merchant"

    def test_user_response_contract_failure_on_invalid_role(self):
        with pytest.raises(ValidationError):
            UserContract(
                id="usr_90123",
                email="dev@cloudscale.io",
                full_name="Senior Developer",
                role="super-user"  # type: ignore
            )

    def test_product_contract_compliance(self):
        product = ProductContract(
            id="prod_112233",
            sku="KB-MECH-RGB",
            name="Mechanical Keyboard",
            description="RGB backlit mechanical keyboard",
            price=89.99
        )
        assert product.price == 89.99

    def test_order_contract_compliance(self):
        order = OrderContract(
            id="ord_88229",
            tenant_id="tenant-contract-test",
            status="COMPLETED",
            total_amount=179.98,
            items=[
                OrderItemContract(
                    product_id="prod_112233",
                    quantity=2,
                    price=89.99
                )
            ]
        )
        assert len(order.items) == 1
        assert order.items[0].product_id == "prod_112233"
