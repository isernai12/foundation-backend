import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BeneficiaryCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="Beneficiary Full Name")
    member_id: Optional[str] = Field(None, description="Optional linked Member UUID")
    mobile: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    national_id: Optional[str] = None
    father_or_husband_name: Optional[str] = None
    occupation: Optional[str] = None
    remarks: Optional[str] = None
    relation_to_member: Optional[str] = None
    assistance_type: Optional[str] = None
    status: str = Field("ACTIVE", description="ACTIVE or INACTIVE")


class BeneficiaryUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    member_id: Optional[str] = None
    mobile: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    national_id: Optional[str] = None
    father_or_husband_name: Optional[str] = None
    occupation: Optional[str] = None
    remarks: Optional[str] = None
    relation_to_member: Optional[str] = None
    assistance_type: Optional[str] = None
    status: Optional[str] = None


class BeneficiaryResponse(BaseModel):
    id: str
    beneficiary_id: str
    member_id: Optional[str] = None
    member_name: Optional[str] = None
    full_name: str
    mobile: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    national_id: Optional[str] = None
    father_or_husband_name: Optional[str] = None
    occupation: Optional[str] = None
    remarks: Optional[str] = None
    relation_to_member: Optional[str] = None
    assistance_type: Optional[str] = None
    status: str
    created_at: datetime.datetime


class BeneficiaryListResponse(BaseModel):
    items: List[BeneficiaryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
