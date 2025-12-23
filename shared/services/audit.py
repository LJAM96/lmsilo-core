"""Audit logging service."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.audit import AuditLog

# Try to use xxhash for performance, fallback to hashlib
try:
    import xxhash
    def compute_hash(content: bytes) -> str:
        return xxhash.xxh3_64(content).hexdigest()
except ImportError:
    import hashlib
    def compute_hash(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


class AuditLogger:
    """
    Service for logging audit events across all LMSilo services.
    
    Captures user identity, file info, and processing metrics.
    """
    
    def __init__(self, service: str):
        """
        Initialize audit logger for a specific service.
        
        Args:
            service: Service name (locate, transcribe, translate)
        """
        self.service = service
    
    async def log(
        self,
        session: AsyncSession,
        action: str,
        request: Optional[Request] = None,
        job_id: Optional[UUID] = None,
        file_content: Optional[bytes] = None,
        file_hash: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        model_used: Optional[str] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """
        Log an audit event.
        
        Args:
            session: Database session
            action: Action type (job_created, job_completed, etc.)
            request: FastAPI request for user identification
            job_id: Associated job ID
            file_content: File bytes for hashing (or use file_hash directly)
            file_hash: Pre-computed file hash
            file_name: Original filename
            file_size_bytes: File size in bytes
            processing_time_ms: Processing duration
            model_used: Model name/ID
            status: Result status (success, failed)
            error_message: Error details if failed
            metadata: Additional flexible data
        
        Returns:
            Created AuditLog record
        """
        # Extract user info from request
        username = None
        ip_address = None
        user_agent = None
        
        if request:
            username = self.get_username(request)
            ip_address = self.get_ip_address(request)
            user_agent = request.headers.get("user-agent")
        
        # Hash file if provided (use pre-computed hash if available)
        computed_hash = file_hash
        computed_size = file_size_bytes
        if file_content and not file_hash:
            computed_hash = compute_hash(file_content)
            computed_size = len(file_content)
        
        # Create audit log entry
        audit = AuditLog(
            service=self.service,
            action=action,
            timestamp=datetime.utcnow(),
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            job_id=job_id,
            file_hash=computed_hash,
            file_name=file_name,
            file_size_bytes=computed_size,
            processing_time_ms=processing_time_ms,
            model_used=model_used,
            status=status,
            error_message=error_message,
            metadata=metadata,
        )
        
        session.add(audit)
        await session.commit()
        await session.refresh(audit)
        
        return audit
    
    @staticmethod
    def get_username(request: Request) -> str:
        """
        Extract username from request.
        
        Priority:
        1. X-Remote-User header (Windows auth proxy)
        2. X-Forwarded-User header
        3. Authorization header (extract from JWT if present)
        4. "anonymous"
        """
        # Windows auth proxy header
        remote_user = request.headers.get("x-remote-user")
        if remote_user:
            return remote_user
        
        # Alternative header
        forwarded_user = request.headers.get("x-forwarded-user")
        if forwarded_user:
            return forwarded_user
        
        # Check for auth header (could parse JWT here)
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Could decode JWT to get username
            # For now, just indicate authenticated user
            return "authenticated_user"
        
        return "anonymous"
    
    @staticmethod
    def get_ip_address(request: Request) -> str:
        """
        Extract client IP address from request.
        
        Handles proxied requests via X-Forwarded-For.
        """
        # Check for forwarded header (proxied requests)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Use direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
