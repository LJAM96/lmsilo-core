"""
Dead-Letter Queue (DLQ) for failed Celery tasks.

Captures failed jobs for debugging, analysis, and manual retry.
"""

import logging
import json
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Text, DateTime, Integer, select, desc
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DLQBase(DeclarativeBase):
    """Base class for DLQ models."""
    pass


class FailedJob(DLQBase):
    """
    Model for storing failed Celery tasks.
    
    Captures all information needed to debug and retry failed jobs.
    """
    
    __tablename__ = "failed_jobs"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Task identification
    service: Mapped[str] = mapped_column(String(20))  # locate, transcribe, translate
    task_name: Mapped[str] = mapped_column(String(100))
    task_id: Mapped[str] = mapped_column(String(100), unique=True)
    
    # Original job reference
    job_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    
    # Failure details
    error_type: Mapped[str] = mapped_column(String(100))
    error_message: Mapped[str] = mapped_column(Text)
    traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Task arguments for retry
    args: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    kwargs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Metadata
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    failed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    retried_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, retrying, resolved, abandoned
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "service": self.service,
            "task_name": self.task_name,
            "task_id": self.task_id,
            "job_id": str(self.job_id) if self.job_id else None,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "args": self.args,
            "kwargs": self.kwargs,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "retried_at": self.retried_at.isoformat() if self.retried_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "status": self.status,
        }


class DeadLetterQueue:
    """
    Dead-letter queue manager for handling failed Celery tasks.
    
    Usage:
        dlq = DeadLetterQueue("transcribe")
        
        # In Celery task error handler
        @app.task(bind=True)
        def my_task(self, job_id):
            try:
                # do work
            except Exception as e:
                await dlq.capture(
                    session=session,
                    task_id=self.request.id,
                    task_name="my_task",
                    job_id=job_id,
                    error=e,
                    args=[job_id],
                )
                raise
    """
    
    def __init__(self, service: str):
        """
        Initialize DLQ for a service.
        
        Args:
            service: Service name (locate, transcribe, translate)
        """
        self.service = service
    
    async def capture(
        self,
        session: AsyncSession,
        task_id: str,
        task_name: str,
        error: Exception,
        job_id: Optional[UUID] = None,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
        max_retries: int = 3,
    ) -> FailedJob:
        """
        Capture a failed task in the dead-letter queue.
        
        Args:
            session: Database session
            task_id: Celery task ID
            task_name: Task function name
            error: Exception that caused failure
            job_id: Original job UUID if applicable
            args: Task positional arguments
            kwargs: Task keyword arguments
            max_retries: Maximum retry attempts
        
        Returns:
            Created FailedJob record
        """
        import traceback as tb
        
        failed_job = FailedJob(
            service=self.service,
            task_id=task_id,
            task_name=task_name,
            job_id=job_id,
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=tb.format_exc(),
            args=args,
            kwargs=kwargs,
            max_retries=max_retries,
            status="pending",
        )
        
        session.add(failed_job)
        await session.commit()
        await session.refresh(failed_job)
        
        logger.warning(
            f"Job captured in DLQ: service={self.service}, "
            f"task={task_name}, error={type(error).__name__}: {error}"
        )
        
        return failed_job
    
    async def list_failed(
        self,
        session: AsyncSession,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[FailedJob]:
        """
        List failed jobs.
        
        Args:
            session: Database session
            status: Filter by status (pending, retrying, resolved, abandoned)
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            List of FailedJob records
        """
        query = select(FailedJob).where(FailedJob.service == self.service)
        
        if status:
            query = query.where(FailedJob.status == status)
        
        query = query.order_by(desc(FailedJob.failed_at)).limit(limit).offset(offset)
        
        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_id(self, session: AsyncSession, dlq_id: UUID) -> Optional[FailedJob]:
        """Get a specific failed job by ID."""
        result = await session.execute(
            select(FailedJob).where(
                FailedJob.id == dlq_id,
                FailedJob.service == self.service
            )
        )
        return result.scalar_one_or_none()
    
    async def mark_retrying(self, session: AsyncSession, dlq_id: UUID) -> Optional[FailedJob]:
        """Mark a failed job as being retried."""
        job = await self.get_by_id(session, dlq_id)
        if job:
            job.status = "retrying"
            job.retried_at = datetime.utcnow()
            job.retry_count += 1
            await session.commit()
        return job
    
    async def mark_resolved(self, session: AsyncSession, dlq_id: UUID) -> Optional[FailedJob]:
        """Mark a failed job as resolved (successfully retried or manually fixed)."""
        job = await self.get_by_id(session, dlq_id)
        if job:
            job.status = "resolved"
            job.resolved_at = datetime.utcnow()
            await session.commit()
        return job
    
    async def mark_abandoned(self, session: AsyncSession, dlq_id: UUID) -> Optional[FailedJob]:
        """Mark a failed job as abandoned (won't be retried)."""
        job = await self.get_by_id(session, dlq_id)
        if job:
            job.status = "abandoned"
            await session.commit()
        return job
    
    async def delete(self, session: AsyncSession, dlq_id: UUID) -> bool:
        """Delete a failed job record."""
        job = await self.get_by_id(session, dlq_id)
        if job:
            await session.delete(job)
            await session.commit()
            return True
        return False
    
    async def get_stats(self, session: AsyncSession) -> dict:
        """Get DLQ statistics."""
        from sqlalchemy import func
        
        result = await session.execute(
            select(FailedJob.status, func.count(FailedJob.id))
            .where(FailedJob.service == self.service)
            .group_by(FailedJob.status)
        )
        
        counts = {status: count for status, count in result.all()}
        
        return {
            "service": self.service,
            "pending": counts.get("pending", 0),
            "retrying": counts.get("retrying", 0),
            "resolved": counts.get("resolved", 0),
            "abandoned": counts.get("abandoned", 0),
            "total": sum(counts.values()),
        }


# Pydantic schemas for API
class FailedJobResponse(BaseModel):
    """API response for failed job."""
    id: str
    service: str
    task_name: str
    task_id: str
    job_id: Optional[str]
    error_type: str
    error_message: str
    traceback: Optional[str]
    retry_count: int
    max_retries: int
    failed_at: Optional[str]
    status: str


class DLQStatsResponse(BaseModel):
    """API response for DLQ statistics."""
    service: str
    pending: int
    retrying: int
    resolved: int
    abandoned: int
    total: int


def create_dlq_router(
    dlq: DeadLetterQueue,
    get_session,
    retry_task_fn=None,
) -> APIRouter:
    """
    Create FastAPI router for DLQ management.
    
    Args:
        dlq: DeadLetterQueue instance
        get_session: Dependency for getting database session
        retry_task_fn: Optional function to retry a task (receives FailedJob)
    
    Returns:
        FastAPI router
    """
    router = APIRouter()
    
    @router.get("", response_model=List[FailedJobResponse])
    async def list_failed_jobs(
        status: Optional[str] = Query(None, description="Filter by status"),
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        session: AsyncSession = Depends(get_session),
    ):
        """List failed jobs in dead-letter queue."""
        jobs = await dlq.list_failed(session, status=status, limit=limit, offset=offset)
        return [job.to_dict() for job in jobs]
    
    @router.get("/stats", response_model=DLQStatsResponse)
    async def get_dlq_stats(session: AsyncSession = Depends(get_session)):
        """Get DLQ statistics."""
        return await dlq.get_stats(session)
    
    @router.get("/{dlq_id}")
    async def get_failed_job(
        dlq_id: UUID,
        session: AsyncSession = Depends(get_session),
    ):
        """Get a specific failed job."""
        job = await dlq.get_by_id(session, dlq_id)
        if not job:
            raise HTTPException(status_code=404, detail="Failed job not found")
        return job.to_dict()
    
    @router.post("/{dlq_id}/retry")
    async def retry_failed_job(
        dlq_id: UUID,
        session: AsyncSession = Depends(get_session),
    ):
        """Retry a failed job."""
        job = await dlq.get_by_id(session, dlq_id)
        if not job:
            raise HTTPException(status_code=404, detail="Failed job not found")
        
        if job.retry_count >= job.max_retries:
            raise HTTPException(
                status_code=400,
                detail=f"Max retries ({job.max_retries}) exceeded"
            )
        
        await dlq.mark_retrying(session, dlq_id)
        
        # Dispatch retry if function provided
        if retry_task_fn:
            try:
                retry_task_fn(job)
            except Exception as e:
                logger.error(f"Failed to dispatch retry: {e}")
                raise HTTPException(status_code=500, detail=f"Retry dispatch failed: {e}")
        
        return {"message": "Job queued for retry", "retry_count": job.retry_count}
    
    @router.post("/{dlq_id}/resolve")
    async def resolve_failed_job(
        dlq_id: UUID,
        session: AsyncSession = Depends(get_session),
    ):
        """Mark a failed job as resolved."""
        job = await dlq.mark_resolved(session, dlq_id)
        if not job:
            raise HTTPException(status_code=404, detail="Failed job not found")
        return {"message": "Job marked as resolved"}
    
    @router.post("/{dlq_id}/abandon")
    async def abandon_failed_job(
        dlq_id: UUID,
        session: AsyncSession = Depends(get_session),
    ):
        """Mark a failed job as abandoned (won't retry)."""
        job = await dlq.mark_abandoned(session, dlq_id)
        if not job:
            raise HTTPException(status_code=404, detail="Failed job not found")
        return {"message": "Job marked as abandoned"}
    
    @router.delete("/{dlq_id}")
    async def delete_failed_job(
        dlq_id: UUID,
        session: AsyncSession = Depends(get_session),
    ):
        """Delete a failed job record."""
        deleted = await dlq.delete(session, dlq_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Failed job not found")
        return {"message": "Job deleted"}
    
    return router
