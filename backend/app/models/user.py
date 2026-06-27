import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, Boolean, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(20), primary_key=True) # ADMIN, MANAGER, ENGINEER, OPERATOR, VIEWER
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False) # e.g. ["doc:upload", "chat:write"]

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="role")

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    role: Mapped["Role"] = relationship(back_populates="users")
    chats: Mapped[list["Chat"]] = relationship(back_populates="user")
    uploaded_versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="uploader")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
