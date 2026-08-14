import uuid
import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Campaign(Base):
    __tablename__ = "Campaign"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaignId: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    targetAmount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    startDate: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endDate: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, COMPLETED, CANCELLED
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    contributions: Mapped[List["CampaignContribution"]] = relationship("CampaignContribution", back_populates="campaign")
    beneficiaryPayments: Mapped[List["BeneficiaryPayment"]] = relationship("BeneficiaryPayment", back_populates="campaign")


class CampaignContribution(Base):
    __tablename__ = "CampaignContribution"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaignId: Mapped[str] = mapped_column(String(36), ForeignKey("Campaign.id", ondelete="RESTRICT"), nullable=False, index=True)
    memberId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Member.id", ondelete="SET NULL"), nullable=True, index=True)
    donorId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Donor.id", ondelete="SET NULL"), nullable=True, index=True)
    ledgerTransactionId: Mapped[str] = mapped_column(
        String(36), ForeignKey("LedgerTransaction.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="contributions", lazy="joined")
    member: Mapped[Optional["Member"]] = relationship("Member", lazy="joined")
    donor: Mapped[Optional["Donor"]] = relationship("Donor", lazy="joined")
    ledgerTransaction: Mapped["LedgerTransaction"] = relationship("LedgerTransaction", lazy="joined")


class BeneficiaryPayment(Base):
    __tablename__ = "BeneficiaryPayment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaignId: Mapped[str] = mapped_column(String(36), ForeignKey("Campaign.id", ondelete="RESTRICT"), nullable=False, index=True)
    beneficiaryId: Mapped[str] = mapped_column(String(36), ForeignKey("Beneficiary.id", ondelete="RESTRICT"), nullable=False, index=True)
    ledgerTransactionId: Mapped[str] = mapped_column(
        String(36), ForeignKey("LedgerTransaction.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    referenceNumber: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="beneficiaryPayments", lazy="joined")
    beneficiary: Mapped["Beneficiary"] = relationship("Beneficiary", back_populates="beneficiaryPayments", lazy="joined")
    ledgerTransaction: Mapped["LedgerTransaction"] = relationship("LedgerTransaction", lazy="joined")
