import uuid
import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Fund(Base):
    __tablename__ = "Fund"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    groupId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Group.id", ondelete="RESTRICT"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="funds", lazy="joined")
    ledgerEntries: Mapped[List["LedgerEntry"]] = relationship("LedgerEntry", back_populates="fund", cascade="all, delete-orphan")
