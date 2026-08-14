import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DonorCreateNested(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    mobile: str = Field(..., min_length=5, max_length=50)
    address: Optional[str] = None
    national_id: Optional[str] = None
    notes: Optional[str] = None


class SadaqahReceiveRequest(BaseModel):
    contributor_type: str = Field(..., description="Contributor classification: 'MEMBER' or 'EXTERNAL'")
    member_id: Optional[str] = Field(None, description="Member UUID (required if contributor_type == 'MEMBER')")
    donor_id: Optional[str] = Field(None, description="Donor UUID (required if contributor_type == 'EXTERNAL' and donor_info not provided)")
    donor_info: Optional[DonorCreateNested] = Field(None, description="Optional nested donor payload to register new external donor inline")
    group_id: Optional[str] = Field(None, description="Target group UUID (village group or Foundation Group)")
    fund_id: Optional[str] = Field(None, description="Target fund UUID (defaults to group fund or central general fund)")
    amount: int = Field(..., gt=0, description="Sadaqah amount (strictly positive integer)")
    date: Optional[datetime.datetime] = Field(None, description="Transaction date (defaults to current time)")
    payment_method: Optional[str] = Field("CASH", description="Payment method: CASH, BANK, MOBILE_BANKING")
    purpose: Optional[str] = Field(None, description="Sadaqah purpose or designation")
    notes: Optional[str] = Field(None, description="Administrative remarks or notes")

    @field_validator("contributor_type")
    @classmethod
    def validate_contributor_type(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in ["MEMBER", "EXTERNAL", "DONOR"]:
            raise ValueError("contributor_type must be either 'MEMBER' or 'EXTERNAL'")
        return "EXTERNAL" if upper == "DONOR" else upper


class SadaqahResponse(BaseModel):
    id: str
    date: datetime.datetime
    type: str
    contributor_type: str
    member_id: Optional[str] = None
    member_name: Optional[str] = None
    member_code: Optional[str] = None
    donor_id: Optional[str] = None
    donor_name: Optional[str] = None
    donor_code: Optional[str] = None
    amount: int
    fund_id: str
    fund_name: str
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime.datetime


class SadaqahListResponse(BaseModel):
    items: List[SadaqahResponse]
    total: int
    total_amount: int
    page: int
    page_size: int
    total_pages: int
