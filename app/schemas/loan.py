import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class QardHasanaCreateRequest(BaseModel):
    member_id: Optional[str] = Field(None, description="Optional Member UUID if recipient is a member")
    beneficiary_id: Optional[str] = Field(None, description="Optional Beneficiary UUID if recipient is a non-member beneficiary")
    amount: int = Field(..., gt=0, description="Qard-e-Hasana principal amount (strictly positive)")
    loan_type: str = Field("OTHER", description="Classification: 'BUSINESS' or 'OTHER'")
    business_type: Optional[str] = Field(None, description="Type of business if loan_type == 'BUSINESS'")
    purpose: str = Field(..., min_length=2, max_length=255, description="Purpose of Qard-e-Hasana")
    requested_date: Optional[datetime.datetime] = Field(None, description="Request / application date")
    installment_type: Optional[str] = Field("MONTHLY", description="DAILY, WEEKLY, MONTHLY, CUSTOM")
    installment_amount: Optional[int] = Field(None, gt=0, description="Repayment installment amount")
    total_installments: Optional[int] = Field(None, gt=0, description="Total expected installments")
    first_installment_date: Optional[datetime.datetime] = Field(None, description="Date first installment is due")
    notes: Optional[str] = Field(None, description="Administrative remarks or collateral notes")
    group_id: Optional[str] = Field(None, description="Group fund from which Qard-e-Hasana is disbursed")


class QardHasanaUpdateRequest(BaseModel):
    purpose: Optional[str] = None
    notes: Optional[str] = None
    installment_type: Optional[str] = None
    installment_amount: Optional[int] = None
    total_installments: Optional[int] = None
    next_due_date: Optional[datetime.datetime] = None
    status: Optional[str] = None


class QardHasanaResponse(BaseModel):
    id: str
    loan_number: str
    member_id: Optional[str] = None
    member_name: Optional[str] = None
    beneficiary_id: Optional[str] = None
    beneficiary_name: Optional[str] = None
    amount: int
    total_paid_amount: int
    remaining_balance: int
    loan_type: str
    business_type: Optional[str] = None
    purpose: str
    requested_date: datetime.datetime
    disbursed_date: Optional[datetime.datetime] = None
    status: str
    installment_type: Optional[str] = None
    installment_amount: Optional[int] = None
    total_installments: Optional[int] = None
    first_installment_date: Optional[datetime.datetime] = None
    next_due_date: Optional[datetime.datetime] = None
    notes: Optional[str] = None
    created_at: datetime.datetime


class QardHasanaListResponse(BaseModel):
    items: List[QardHasanaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RepaymentCreateRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Repayment amount (cannot exceed remaining balance)")
    payment_method: str = Field("CASH", description="Payment method: CASH, BANK, MOBILE_BANKING")
    reference_number: Optional[str] = Field(None, description="Receipt / voucher number")
    installment_no: Optional[int] = Field(None, description="Installment sequence number")
    notes: Optional[str] = Field(None, description="Repayment notes")
    collected_by: Optional[str] = Field(None, description="Collector name or employee ID")
    payment_date: Optional[datetime.datetime] = Field(None, description="Repayment date")


class RepaymentResponse(BaseModel):
    id: str
    loan_id: str
    amount: int
    date: datetime.datetime
    status: str
    installment_no: Optional[int] = None
    payment_method: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    remaining_loan_balance: int
    loan_status: str
    ledger_transaction_id: str
    created_at: datetime.datetime


class QardHasanaLedgerItem(BaseModel):
    id: str
    date: datetime.datetime
    type: str  # "DISBURSEMENT" or "REPAYMENT"
    amount: int
    running_balance: int
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime


class QardHasanaLedgerResponse(BaseModel):
    loan_id: str
    loan_number: str
    recipient_name: str
    original_amount: int
    total_repaid: int
    current_balance: int
    status: str
    items: List[QardHasanaLedgerItem]
    total: int
    page: int
    page_size: int
    total_pages: int
