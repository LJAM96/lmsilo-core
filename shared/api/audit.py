"""Audit log API routes."""

import csv
import io
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.audit import AuditLog


def create_audit_router(get_session):
    """
    Create audit router with database session dependency.
    
    Args:
        get_session: Async session dependency function
    
    Returns:
        FastAPI router for audit endpoints
    """
    router = APIRouter()
    
    @router.get("", response_model=List[dict])
    async def list_audit_logs(
        service: Optional[str] = Query(default=None),
        username: Optional[str] = Query(default=None),
        action: Optional[str] = Query(default=None),
        from_date: Optional[datetime] = Query(default=None),
        to_date: Optional[datetime] = Query(default=None),
        job_id: Optional[UUID] = Query(default=None),
        limit: int = Query(default=100, le=1000),
        offset: int = Query(default=0),
        session: AsyncSession = Depends(get_session),
    ):
        """
        List audit logs with filters.
        
        Supports filtering by service, user, date range, etc.
        """
        query = select(AuditLog).order_by(desc(AuditLog.timestamp))
        
        filters = []
        
        if service:
            filters.append(AuditLog.service == service)
        if username:
            filters.append(AuditLog.username == username)
        if action:
            filters.append(AuditLog.action == action)
        if from_date:
            filters.append(AuditLog.timestamp >= from_date)
        if to_date:
            filters.append(AuditLog.timestamp <= to_date)
        if job_id:
            filters.append(AuditLog.job_id == job_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.offset(offset).limit(limit)
        
        result = await session.execute(query)
        logs = result.scalars().all()
        
        return [log.to_dict() for log in logs]
    
    @router.get("/export")
    async def export_audit_logs(
        format: str = Query(default="csv", pattern="^(csv|json)$"),
        service: Optional[str] = Query(default=None),
        username: Optional[str] = Query(default=None),
        from_date: Optional[datetime] = Query(default=None),
        to_date: Optional[datetime] = Query(default=None),
        session: AsyncSession = Depends(get_session),
    ):
        """
        Export audit logs as CSV or JSON.
        """
        query = select(AuditLog).order_by(desc(AuditLog.timestamp))
        
        filters = []
        if service:
            filters.append(AuditLog.service == service)
        if username:
            filters.append(AuditLog.username == username)
        if from_date:
            filters.append(AuditLog.timestamp >= from_date)
        if to_date:
            filters.append(AuditLog.timestamp <= to_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        result = await session.execute(query)
        logs = result.scalars().all()
        
        if format == "json":
            import json
            content = json.dumps([log.to_dict() for log in logs], default=str)
            return Response(
                content=content,
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=audit_logs.json"}
            )
        else:
            # CSV export
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "timestamp", "service", "action", "username", "ip_address",
                "job_id", "file_name", "file_hash", "file_size_bytes",
                "processing_time_ms", "model_used", "status", "error_message"
            ])
            
            # Data rows
            for log in logs:
                writer.writerow([
                    log.timestamp.isoformat() if log.timestamp else "",
                    log.service,
                    log.action,
                    log.username or "",
                    log.ip_address or "",
                    str(log.job_id) if log.job_id else "",
                    log.file_name or "",
                    log.file_hash or "",
                    log.file_size_bytes or "",
                    log.processing_time_ms or "",
                    log.model_used or "",
                    log.status or "",
                    log.error_message or "",
                ])
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
            )
    
    @router.get("/stats")
    async def get_audit_stats(
        service: Optional[str] = Query(default=None),
        from_date: Optional[datetime] = Query(default=None),
        to_date: Optional[datetime] = Query(default=None),
        session: AsyncSession = Depends(get_session),
    ):
        """
        Get audit log statistics.
        """
        from sqlalchemy import func
        
        query = select(
            AuditLog.service,
            AuditLog.action,
            func.count(AuditLog.id).label("count"),
            func.avg(AuditLog.processing_time_ms).label("avg_processing_time_ms"),
        ).group_by(AuditLog.service, AuditLog.action)
        
        filters = []
        if service:
            filters.append(AuditLog.service == service)
        if from_date:
            filters.append(AuditLog.timestamp >= from_date)
        if to_date:
            filters.append(AuditLog.timestamp <= to_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        result = await session.execute(query)
        
        return [
            {
                "service": row.service,
                "action": row.action,
                "count": row.count,
                "avg_processing_time_ms": float(row.avg_processing_time_ms) if row.avg_processing_time_ms else None,
            }
            for row in result
        ]
    
    return router
