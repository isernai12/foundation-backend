import uuid
import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Loan(Base):
    __tablename__ = "Loan"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    loanNumber: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    memberId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Member.id", ondelete="RESTRICT"), nullable=True, index=True)
    beneficiaryId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Beneficiary.id", ondelete="RESTRICT"), nullable=True, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    loanType: Mapped[str] = mapped_column(String(50), default="OTHER", nullable=False)  # BUSINESS, OTHER
    businessType: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    requestedDate: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    disbursedDate: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, PAID, DEFAULTED, CANCELLED
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Installment schedule and balance tracking
    installmentType: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # DAILY, WEEKLY, MONTHLY, CUSTOM
    installmentAmount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    totalInstallments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    firstInstallmentDate: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    nextDueDate: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    totalPaidAmount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remainingBalance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    member: Mapped[Optional["Member"]] = relationship("Member", lazy="joined")
    beneficiary: Mapped[Optional["Beneficiary"]] = relationship("Beneficiary", lazy="joined")
    repayments: Mapped[List["LoanRepayment"]] = relationship("LoanRepayment", back_populates="loan", cascade="all, delete-orphan", lazy="selectin")


class LoanRepayment(Base):
    __tablename__ = "LoanRepayment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    loanId: Mapped[str] = mapped_column(String(36), ForeignKey("Loan.id", ondelete="RESTRICT"), nullable=False, index=True)
    ledgerTransactionId: Mapped[str] = mapped_column(
        String(36), ForeignKey("LedgerTransaction.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED", nullable=False)

    installmentNo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    paymentMethod: Mapped[str] = mapped_column(String(50), default="CASH", nullable=False)
    referenceNumber: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collectedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    receiptUrl: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    loan: Mapped["Loan"] = relationship("Loan", back_populates="repayments")
    ledgerTransaction: Mapped[Optional["LedgerTransaction"]] = relationship("LedgerTransaction", lazy="selectin")
