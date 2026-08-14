from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Basic health check response."""
    status: str = "ok"


class DatabaseHealthResponse(BaseModel):
    """Database health check response."""
    status: str
    database: str
    detail: Optional[str] = None


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    type: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
