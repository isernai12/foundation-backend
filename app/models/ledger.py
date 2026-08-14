import uuid
import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class LedgerTransaction(Base):
    __tablename__ = "LedgerTransaction"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # DONATION, SADAQAH, CONTRIBUTION
    referenceId: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    memberId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Member.id", ondelete="SET NULL"), nullable=True, index=True)
    donorId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Donor.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    member: Mapped[Optional["Member"]] = relationship("Member", back_populates="donations", lazy="joined")
    donor: Mapped[Optional["Donor"]] = relationship("Donor", back_populates="donations", lazy="joined")
    entries: Mapped[List["LedgerEntry"]] = relationship("LedgerEntry", back_populates="transaction", cascade="all, delete-orphan", lazy="joined")


class LedgerEntry(Base):
    __tablename__ = "LedgerEntry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transactionId: Mapped[str] = mapped_column(String(36), ForeignKey("LedgerTransaction.id", ondelete="CASCADE"), nullable=False, index=True)
    fundId: Mapped[str] = mapped_column(String(36), ForeignKey("Fund.id", ondelete="RESTRICT"), nullable=False, index=True)
    isCredit: Mapped[bool] = mapped_column(Boolean, nullable=False)  # True = Credit (+), False = Debit (-)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    groupId: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    groupCode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    groupName: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    transaction: Mapped["LedgerTransaction"] = relationship("LedgerTransaction", back_populates="entries")
    fund: Mapped["Fund"] = relationship("Fund", back_populates="ledgerEntries", lazy="joined")
