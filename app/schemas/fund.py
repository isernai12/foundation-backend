import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FundCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Fund name (e.g. General Foundation Fund, Flood Relief Fund)")
    description: Optional[str] = None
    group_id: Optional[str] = Field(None, description="Optional Group UUID (None represents central Foundation Fund)")


class FundUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group_id: Optional[str] = None


class FundResponse(BaseModel):
    id: str
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    group_code: Optional[str] = None
    name: str
    description: Optional[str] = None
    current_balance: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime


class FundListResponse(BaseModel):
    items: List[FundResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
