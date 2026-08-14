import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.member import DocumentItem, GroupSummary


class MemberRequestCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="Applicant full name")
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    national_id: Optional[str] = None
    id_document_type: Optional[str] = "NID"
    occupation: Optional[str] = None
    monthly_income: Optional[int] = None
    blood_group: Optional[str] = None
    education: Optional[str] = None
    marital_status: Optional[str] = None
    mobile: Optional[str] = None
    alt_mobile: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    present_address: Optional[str] = None
    permanent_address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_mobile: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    reference_name: Optional[str] = None
    reference_mobile: Optional[str] = None
    reference_relation: Optional[str] = None
    group_id: Optional[str] = Field(None, description="Requested group UUID")
    reason_for_joining: Optional[str] = None
    documents: Optional[List[DocumentItem]] = None


class MemberRequestApprove(BaseModel):
    remarks: Optional[str] = None


class MemberRequestReject(BaseModel):
    reason: str = Field(..., min_length=2, description="Reason for rejection")
    admin_message: Optional[str] = None


class MemberRequestSubmitResponse(BaseModel):
    id: str
    application_number: str
    status: str
    message: str = "Application submitted successfully"


class MemberRequestStatusResponse(BaseModel):
    id: str
    application_number: str
    status: str
    full_name: str
    submitted_at: datetime.datetime
    approved_at: Optional[datetime.datetime] = None
    rejection_reason: Optional[str] = None
    admin_message: Optional[str] = None


class MemberRequestDetailResponse(BaseModel):
    id: str
    application_number: str
    status: str
    full_name: str
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    national_id: Optional[str] = None
    id_document_type: Optional[str] = "NID"
    occupation: Optional[str] = None
    monthly_income: Optional[int] = None
    blood_group: Optional[str] = None
    education: Optional[str] = None
    marital_status: Optional[str] = None
    mobile: Optional[str] = None
    alt_mobile: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    present_address: Optional[str] = None
    permanent_address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_mobile: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    reference_name: Optional[str] = None
    reference_mobile: Optional[str] = None
    reference_relation: Optional[str] = None
    group_id: Optional[str] = None
    group: Optional[GroupSummary] = None
    reason_for_joining: Optional[str] = None
    documents: List[DocumentItem] = []
    rejection_reason: Optional[str] = None
    admin_message: Optional[str] = None
    approved_at: Optional[datetime.datetime] = None
    approved_by: Optional[str] = None
    created_member_id: Optional[str] = None
    submitted_at: datetime.datetime
    updated_at: datetime.datetime


class MemberRequestListResponse(BaseModel):
    items: List[MemberRequestDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
