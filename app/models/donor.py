import uuid
import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class Donor(Base):
    __tablename__ = "Donor"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    donorId: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    fullName: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nationalId: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    donations: Mapped[List["LedgerTransaction"]] = relationship("LedgerTransaction", back_populates="donor")
