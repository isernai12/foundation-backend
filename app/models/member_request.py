import uuid
import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class MemberRequest(Base):
    __tablename__ = "MemberRequest"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    applicationNumber: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, REJECTED, NEEDS_CHANGES

    # Personal Information
    fullName: Mapped[str] = mapped_column(String(255), nullable=False)
    fatherName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    motherName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dob: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nationalId: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    idDocumentType: Mapped[Optional[str]] = mapped_column(String(50), default="NID", nullable=True)
    occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    monthlyIncome: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bloodGroup: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    education: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    maritalStatus: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Contact Information
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    altMobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    presentAddress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permanentAddress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Emergency Contact
    emergencyContactName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emergencyContactMobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    emergencyContactRelation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Reference / Nominee
    referenceName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    referenceMobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    referenceRelation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Organization
    groupId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Group.id", ondelete="SET NULL"), nullable=True, index=True)
    reasonForJoining: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Documents JSON: array of { title, cloudinaryPublicId, secureUrl }
    documents: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Admin Workflow
    rejectionReason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    adminMessage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approvedAt: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approvedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    createdMemberId: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    submittedAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="memberRequests", lazy="joined")
