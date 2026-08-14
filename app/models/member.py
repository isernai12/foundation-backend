import uuid
import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Member(Base):
    __tablename__ = "Member"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    memberId: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    groupId: Mapped[str] = mapped_column(String(36), ForeignKey("Group.id", ondelete="RESTRICT"), nullable=False, index=True)
    fullName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fatherName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    motherName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dob: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    nationalId: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    idDocumentType: Mapped[Optional[str]] = mapped_column(String(50), default="NID", nullable=True)
    occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    monthlyIncome: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bloodGroup: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    altMobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    presentAddress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permanentAddress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emergencyContactName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emergencyContactMobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    emergencyContactRelation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    joinDate: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False, index=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    maritalStatus: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    workplace: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    skills: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON formatted reference
    reasonForJoining: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    participation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    declarationAccepted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    memberType: Mapped[Optional[str]] = mapped_column(String(50), default="REGULAR", nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(50), default="GENERAL_MEMBER", nullable=True)
    paidUntilMonth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paidUntilYear: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="members", lazy="joined")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="member", cascade="all, delete-orphan")
    statusHistory: Mapped[List["MemberStatusHistory"]] = relationship("MemberStatusHistory", back_populates="member", cascade="all, delete-orphan")
    donations: Mapped[List["LedgerTransaction"]] = relationship("LedgerTransaction", back_populates="member")
    contributions: Mapped[List["MonthlyContribution"]] = relationship("MonthlyContribution", back_populates="member")
    beneficiaries: Mapped[List["Beneficiary"]] = relationship("Beneficiary", back_populates="member")


class MemberStatusHistory(Base):
    __tablename__ = "MemberStatusHistory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    memberId: Mapped[str] = mapped_column(String(36), ForeignKey("Member.id", ondelete="CASCADE"), nullable=False, index=True)
    fromStatus: Mapped[str] = mapped_column(String(50), nullable=False)
    toStatus: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    changedAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)

    # Relationships
    member: Mapped["Member"] = relationship("Member", back_populates="statusHistory")
