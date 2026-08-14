import uuid
import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Beneficiary(Base):
    __tablename__ = "Beneficiary"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    beneficiaryId: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    memberId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Member.id", ondelete="SET NULL"), nullable=True, index=True)
    fullName: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    presentAddress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permanentAddress: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nationalId: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    idDocumentType: Mapped[Optional[str]] = mapped_column(String(50), default="NID", nullable=True)
    fatherOrHusbandName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    occupation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relationToMember: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assistanceType: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assistanceReason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    member: Mapped[Optional["Member"]] = relationship("Member", back_populates="beneficiaries", lazy="joined")
    beneficiaryPayments: Mapped[List["BeneficiaryPayment"]] = relationship("BeneficiaryPayment", back_populates="beneficiary")
