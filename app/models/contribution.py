import uuid
import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class MonthlyContribution(Base):
    __tablename__ = "MonthlyContribution"
    __table_args__ = (
        UniqueConstraint("memberId", "month", "year", "isAdditional", name="uq_member_month_year_additional"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    memberId: Mapped[str] = mapped_column(String(36), ForeignKey("Member.id", ondelete="RESTRICT"), nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    expectedAmount: Mapped[int] = mapped_column(Integer, nullable=False)
    isAdditional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)  # PENDING, PAID, PARTIAL
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    member: Mapped["Member"] = relationship("Member", back_populates="contributions", lazy="joined")
    payments: Mapped[List["ContributionPayment"]] = relationship("ContributionPayment", back_populates="monthlyContribution", cascade="all, delete-orphan", lazy="joined")


class ContributionPayment(Base):
    __tablename__ = "ContributionPayment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    monthlyContributionId: Mapped[str] = mapped_column(
        String(36), ForeignKey("MonthlyContribution.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    ledgerTransactionId: Mapped[str] = mapped_column(
        String(36), ForeignKey("LedgerTransaction.id", ondelete="RESTRICT"), unique=True, nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    paymentDate: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paymentMethod: Mapped[str] = mapped_column(String(50), default="CASH", nullable=False)
    referenceNumber: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    monthlyContribution: Mapped["MonthlyContribution"] = relationship("MonthlyContribution", back_populates="payments")
    ledgerTransaction: Mapped["LedgerTransaction"] = relationship("LedgerTransaction", lazy="joined")
