import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class GroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Group / Village Name")
    code: str = Field(..., min_length=2, max_length=100, description="Unique alphanumeric code (e.g. GRP-DHK-01)")
    short_name: Optional[str] = None
    description: Optional[str] = None
    remarks: Optional[str] = None
    status: str = Field(default="ACTIVE", description="ACTIVE or INACTIVE")
    is_foundation_group: bool = Field(default=False, description="Set True only for the single root Foundation group")
    member_signup_enabled: bool = Field(default=True, description="Whether public registration is enabled for this group")
    foundation_id: Optional[str] = Field(None, description="Optional Foundation UUID")


class GroupUpdateRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    short_name: Optional[str] = None
    description: Optional[str] = None
    remarks: Optional[str] = None
    status: Optional[str] = None
    member_signup_enabled: Optional[bool] = None


class GroupResponse(BaseModel):
    id: str
    foundation_id: str
    name: str
    code: str
    short_name: Optional[str] = None
    description: Optional[str] = None
    remarks: Optional[str] = None
    status: str
    is_foundation_group: bool
    member_signup_enabled: bool
    member_count: int = 0
    current_balance: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime


class GroupListResponse(BaseModel):
    items: List[GroupResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
