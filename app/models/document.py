import uuid
import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class Document(Base):
    __tablename__ = "Document"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    documentNumber: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="IMAGE", nullable=False)  # IMAGE, PDF, DOC
    cloudinaryPublicId: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    secureUrl: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    originalFilename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mimeType: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sizeBytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    targetType: Mapped[str] = mapped_column(String(50), default="MEMBER", nullable=False)  # MEMBER, GROUP, FOUNDATION
    foundationId: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    groupId: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    memberId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Member.id", ondelete="CASCADE"), nullable=True, index=True)
    categoryId: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    createdBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    member: Mapped[Optional["Member"]] = relationship("Member", back_populates="documents")
