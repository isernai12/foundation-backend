import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.sadaqah import DonorCreateNested


class FinancialActivityCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Activity name (e.g. Winter Clothes Distribution 2026)")
    purpose: str = Field(..., min_length=2, max_length=255, description="Purpose or objective")
    description: Optional[str] = None
    target_amount: Optional[int] = Field(None, gt=0, description="Target budget")
    start_date: Optional[datetime.datetime] = Field(None, description="Start date")
    end_date: Optional[datetime.datetime] = Field(None, description="End date")
    status: str = Field("ACTIVE", description="ACTIVE, COMPLETED, CANCELLED")
    remarks: Optional[str] = None


class FinancialActivityUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[int] = None
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    status: Optional[str] = None
    remarks: Optional[str] = None


class FinancialActivityResponse(BaseModel):
    id: str
    activity_id: str
    name: str
    purpose: str
    description: Optional[str] = None
    target_amount: Optional[int] = None
    total_income: int = 0
    total_expense: int = 0
    available_balance: int = 0
    start_date: datetime.datetime
    end_date: Optional[datetime.datetime] = None
    status: str
    remarks: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class FinancialActivityListResponse(BaseModel):
    items: List[FinancialActivityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FinancialActivityIncomeRequest(BaseModel):
    contributor_type: str = Field(..., description="'MEMBER' or 'EXTERNAL'")
    member_id: Optional[str] = Field(None, description="Member UUID")
    donor_id: Optional[str] = Field(None, description="Donor UUID")
    donor_info: Optional[DonorCreateNested] = Field(None, description="New donor payload")
    amount: int = Field(..., gt=0, description="Contribution amount")
    date: Optional[datetime.datetime] = Field(None, description="Contribution date")
    remarks: Optional[str] = Field(None, description="Remarks")


class FinancialActivityDisburseRequest(BaseModel):
    beneficiary_id: str = Field(..., description="Beneficiary UUID")
    amount: int = Field(..., gt=0, description="Disbursement amount")
    reason: str = Field(..., min_length=2, max_length=255, description="Disbursement reason / assistance details")
    date: Optional[datetime.datetime] = Field(None, description="Disbursement date")
    reference_number: Optional[str] = Field(None, description="Optional payment reference / check number")
    comments: Optional[str] = Field(None, description="Optional administrative comments")


class FinancialActivityLedgerEntryItem(BaseModel):
    id: str
    date: datetime.datetime
    type: str  # "INCOME" or "DISBURSEMENT"
    amount: int
    source_or_recipient: str
    reason: Optional[str] = None
    running_balance: int
    reference_number: Optional[str] = None
    created_at: datetime.datetime


class FinancialActivityLedgerResponse(BaseModel):
    activity_id: str
    activity_code: str
    activity_name: str
    current_balance: int
    total_income: int
    total_disbursed: int
    items: List[FinancialActivityLedgerEntryItem]
    total: int
    page: int
    page_size: int
    total_pages: int
