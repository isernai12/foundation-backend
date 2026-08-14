import uuid
import datetime
from typing import List, Optional
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base


class User(Base):
    __tablename__ = "User"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    roleId: Mapped[str] = mapped_column(String(36), ForeignKey("Role.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, SUSPENDED
    lastLogin: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON formatted preferences
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="users", lazy="joined")
    sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    userPermissions: Mapped[List["UserPermission"]] = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")
    auditLogs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")


class Role(Base):
    __tablename__ = "Role"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updatedAt: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="role")
    permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan", lazy="joined"
    )


class Permission(Base):
    __tablename__ = "Permission"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("module", "action", name="uq_permission_module_action"),
    )

    # Relationships
    rolePermissions: Mapped[List["RolePermission"]] = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    userPermissions: Mapped[List["UserPermission"]] = relationship("UserPermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "RolePermission"

    roleId: Mapped[str] = mapped_column(String(36), ForeignKey("Role.id", ondelete="CASCADE"), primary_key=True)
    permissionId: Mapped[str] = mapped_column(String(36), ForeignKey("Permission.id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="rolePermissions", lazy="joined")


class UserPermission(Base):
    __tablename__ = "UserPermission"

    userId: Mapped[str] = mapped_column(String(36), ForeignKey("User.id", ondelete="CASCADE"), primary_key=True)
    permissionId: Mapped[str] = mapped_column(String(36), ForeignKey("Permission.id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="userPermissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="userPermissions", lazy="joined")


class UserSession(Base):
    __tablename__ = "UserSession"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId: Mapped[str] = mapped_column(String(36), ForeignKey("User.id", ondelete="CASCADE"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    device: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ipAddress: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lastActive: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expiresAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "AuditLog"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("User.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    referenceId: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    oldValue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    newValue: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ipAddress: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="auditLogs")
