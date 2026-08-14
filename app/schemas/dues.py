import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SingleDuePayRequest(BaseModel):
    member_id: str = Field(..., description="Member UUID")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    year: int = Field(..., ge=2000, le=2100, description="Year (e.g. 2026)")
    amount: Optional[int] = Field(None, gt=0, description="Payment amount (defaults to configured monthly fee)")
    is_additional: bool = Field(False, description="Whether this is an additional extra contribution")
    payment_date: Optional[datetime.datetime] = Field(None, description="Payment timestamp (defaults to now)")
    payment_method: str = Field("CASH", description="Payment method: CASH, BANK, MOBILE_BANKING")
    reference_number: Optional[str] = Field(None, description="Optional payment reference / voucher number")
    notes: Optional[str] = Field(None, description="Optional remarks")


class MultiMonthDuePayRequest(BaseModel):
    member_id: str = Field(..., description="Member UUID")
    from_month: int = Field(..., ge=1, le=12, description="Starting month (1-12)")
    from_year: int = Field(..., ge=2000, le=2100, description="Starting year")
    to_month: int = Field(..., ge=1, le=12, description="Ending month (1-12)")
    to_year: int = Field(..., ge=2000, le=2100, description="Ending year")
    amount_per_month: Optional[int] = Field(None, gt=0, description="Fee per month (defaults to configured monthly fee)")
    payment_date: Optional[datetime.datetime] = Field(None, description="Payment timestamp (defaults to now)")
    payment_method: str = Field("CASH", description="Payment method: CASH, BANK, MOBILE_BANKING")
    reference_number: Optional[str] = Field(None, description="Optional payment reference / voucher number")
    notes: Optional[str] = Field(None, description="Optional remarks")


class PaidMonthDetail(BaseModel):
    month: int
    year: int
    amount: int
    monthly_contribution_id: str


class DuePaymentResponse(BaseModel):
    success: bool = True
    member_id: str
    total_amount_paid: int
    months_paid: List[PaidMonthDetail]
    paid_until_month: Optional[int] = None
    paid_until_year: Optional[int] = None
    ledger_transaction_id: str
    message: str


class MemberDuesSummaryResponse(BaseModel):
    member_id: str
    member_code: str
    full_name: str
    mobile: Optional[str] = None
    group_id: str
    group_name: str
    join_date: Optional[datetime.datetime] = None
    current_monthly_fee: int
    paid_until_month: Optional[int] = None
    paid_until_year: Optional[int] = None
    total_paid_amount: int
    total_due_amount: int
    status: str


class MemberDuesLedgerItem(BaseModel):
    id: str
    monthly_contribution_id: str
    month: int
    year: int
    expected_amount: int
    paid_amount: int
    is_additional: bool
    status: str
    payment_date: Optional[datetime.datetime] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    ledger_transaction_id: Optional[str] = None


class MemberDuesLedgerResponse(BaseModel):
    member_id: str
    items: List[MemberDuesLedgerItem]
    total: int
    page: int
    page_size: int
    total_pages: int
