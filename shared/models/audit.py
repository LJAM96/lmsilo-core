"""Audit log database model."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import String, Text, DateTime, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID, JSONB


class Base(DeclarativeBase):
    """Base class for shared models."""
    pass


class AuditLog(Base):
    """
    Audit log model for tracking all service usage.
    
    Captures user identity, file info, processing metrics,
    and results for compliance and debugging.
    """
    
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Service identification
    service: Mapped[str] = mapped_column(String(20))  # locate, transcribe, translate
    action: Mapped[str] = mapped_column(String(50))   # job_created, job_completed, etc.
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # User identification
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Job reference
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # File info
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Processing metrics
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Result
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # success, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Flexible metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "service": self.service,
            "action": self.action,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "username": self.username,
            "ip_address": self.ip_address,
            "job_id": str(self.job_id) if self.job_id else None,
            "file_hash": self.file_hash,
            "file_name": self.file_name,
            "file_size_bytes": self.file_size_bytes,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "status": self.status,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }
