import math
from collections.abc import Sequence
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

class PageParams(BaseModel):
    """Query parameters for handling list pagination."""
    page: int = Field(default=1, ge=1, description="Page number starting at 1")
    size: int = Field(default=10, ge=1, le=100, description="Items limit per page (Max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

class Page(BaseModel, Generic[T]):
    """Standardized response schema for paginated resource lists."""
    items: Sequence[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: Sequence[T], total: int, params: PageParams) -> "Page[T]":
        pages = math.ceil(total / params.size) if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=pages
        )
