import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class ReferenceInfo(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    relation: Optional[str] = None


class DocumentItem(BaseModel):
    title: str
    type: str = "IMAGE"
    cloudinary_public_id: Optional[str] = None
    secure_url: Optional[str] = None


class GroupSummary(BaseModel):
    id: str
    name: str
    code: str


class MemberCreateRequest(BaseModel):
    group_id: str = Field(..., description="Target group UUID")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full Name of the Member")
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime.datetime] = None
    national_id: Optional[str] = None
    id_document_type: Optional[str] = "NID"
    occupation: Optional[str] = None
    monthly_income: Optional[int] = None
    blood_group: Optional[str] = None
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
    reference: Optional[ReferenceInfo] = None
    join_date: Optional[datetime.datetime] = None
    remarks: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    workplace: Optional[str] = None
    designation: Optional[str] = None
    skills: Optional[str] = None
    reason_for_joining: Optional[str] = None
    member_type: Optional[str] = "REGULAR"
    position: Optional[str] = "GENERAL_MEMBER"
    status: Optional[str] = "ACTIVE"
    member_id: Optional[str] = Field(None, description="Optional custom Member ID (e.g. M-0001); generated automatically if omitted")
    documents: Optional[List[DocumentItem]] = None


class MemberUpdateRequest(BaseModel):
    group_id: Optional[str] = None
    full_name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime.datetime] = None
    national_id: Optional[str] = None
    id_document_type: Optional[str] = None
    occupation: Optional[str] = None
    monthly_income: Optional[int] = None
    blood_group: Optional[str] = None
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
    reference: Optional[ReferenceInfo] = None
    join_date: Optional[datetime.datetime] = None
    remarks: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    workplace: Optional[str] = None
    designation: Optional[str] = None
    skills: Optional[str] = None
    reason_for_joining: Optional[str] = None
    member_type: Optional[str] = None
    position: Optional[str] = None
    status: Optional[str] = None
    documents: Optional[List[DocumentItem]] = None


class MemberStatusHistoryResponse(BaseModel):
    id: str
    from_status: str
    to_status: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    changed_by: Optional[str] = None
    changed_at: datetime.datetime


class DocumentResponse(BaseModel):
    id: str
    document_number: str
    title: str
    type: str
    cloudinary_public_id: Optional[str] = None
    secure_url: Optional[str] = None
    size_bytes: int


class MemberResponse(BaseModel):
    id: str
    member_id: str
    group_id: str
    group_name: Optional[str] = None
    group_code: Optional[str] = None
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    status: str
    member_type: Optional[str] = "REGULAR"
    position: Optional[str] = "GENERAL_MEMBER"
    join_date: Optional[datetime.datetime] = None
    created_at: datetime.datetime


class MemberDetailResponse(BaseModel):
    id: str
    member_id: str
    group_id: str
    group: Optional[GroupSummary] = None
    full_name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[datetime.datetime] = None
    national_id: Optional[str] = None
    id_document_type: Optional[str] = "NID"
    occupation: Optional[str] = None
    monthly_income: Optional[int] = None
    blood_group: Optional[str] = None
    mobile: Optional[str] = None
    alt_mobile: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    present_address: Optional[str] = None
    permanent_address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_mobile: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    reference: Optional[ReferenceInfo] = None
    join_date: Optional[datetime.datetime] = None
    remarks: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    workplace: Optional[str] = None
    designation: Optional[str] = None
    skills: Optional[str] = None
    reason_for_joining: Optional[str] = None
    member_type: Optional[str] = "REGULAR"
    position: Optional[str] = "GENERAL_MEMBER"
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    documents: List[DocumentResponse] = []
    status_history: List[MemberStatusHistoryResponse] = []


class MemberListResponse(BaseModel):
    items: List[MemberResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
