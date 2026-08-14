import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PermissionItem(BaseModel):
    id: str
    module: str
    action: str
    code: str
    description: Optional[str] = None
    name_en: Optional[str] = None
    name_bn: Optional[str] = None


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Role name (e.g. Field Officer, Auditor)")
    description: Optional[str] = Field(None, description="Role description")
    permission_ids: Optional[List[str]] = Field(default=[], description="List of Permission UUIDs to assign")


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    permission_ids: Optional[List[str]] = Field(None, description="Updated list of Permission UUIDs")


class RoleDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_super_admin: bool = False
    user_count: int = 0
    permissions_count: int = 0
    permissions: List[PermissionItem] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime


class RoleListResponse(BaseModel):
    items: List[RoleDetailResponse]
    total: int


class PermissionListResponse(BaseModel):
    items: List[PermissionItem]
    total: int
    modules: List[str]
