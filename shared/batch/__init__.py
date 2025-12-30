"""
Batch import module for LMSilo services.

Provides common utilities for importing jobs from CSV files or folders.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Awaitable
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """Batch job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL = "partial"  # Some items failed
    FAILED = "failed"


@dataclass
class BatchItem:
    """Single item in a batch."""
    index: int
    file_path: str
    options: Dict[str, Any] = field(default_factory=dict)
    job_id: Optional[UUID] = None
    status: str = "pending"
    error: Optional[str] = None


@dataclass
class BatchResult:
    """Result of batch processing."""
    batch_id: str
    total_items: int
    processed: int = 0
    successful: int = 0
    failed: int = 0
    status: BatchStatus = BatchStatus.PENDING
    items: List[BatchItem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BatchImportRequest(BaseModel):
    """Request for folder-based batch import."""
    folder_path: str
    recursive: bool = False
    file_pattern: Optional[str] = None  # e.g., "*.jpg" or "*.mp3"
    options: Optional[Dict[str, Any]] = None


class BatchImportResponse(BaseModel):
    """Response for batch import."""
    batch_id: str
    total_items: int
    status: str
    message: str


class BatchStatusResponse(BaseModel):
    """Batch status response."""
    batch_id: str
    total_items: int
    processed: int
    successful: int
    failed: int
    status: str
    job_ids: List[str]


class BatchImporter:
    """
    Base class for batch import operations.
    
    Each service should extend this with service-specific logic.
    
    Example usage:
        class LocateBatchImporter(BatchImporter):
            async def create_job(self, file_path, options):
                # Create locate job
                pass
        
        importer = LocateBatchImporter(
            allowed_extensions={'.jpg', '.png'},
            max_items=100,
        )
        
        router = importer.create_router(get_session)
    """
    
    def __init__(
        self,
        service_name: str,
        allowed_extensions: set[str],
        max_items: int = 100,
        default_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize batch importer.
        
        Args:
            service_name: Name of the service (locate, transcribe, translate)
            allowed_extensions: Set of allowed file extensions (e.g., {'.jpg', '.png'})
            max_items: Maximum items per batch
            default_options: Default options for job creation
        """
        self.service_name = service_name
        self.allowed_extensions = allowed_extensions
        self.max_items = max_items
        self.default_options = default_options or {}
        self._batches: Dict[str, BatchResult] = {}
    
    async def create_job(
        self,
        file_path: Path,
        options: Dict[str, Any],
        session: Any,
    ) -> UUID:
        """
        Create a job for a single file.
        
        Override this in service-specific implementations.
        
        Args:
            file_path: Path to the file
            options: Job options
            session: Database session
        
        Returns:
            Created job UUID
        """
        raise NotImplementedError("Subclass must implement create_job")
    
    def validate_file(self, file_path: Path) -> bool:
        """Check if file is valid for processing."""
        if not file_path.exists():
            return False
        if not file_path.is_file():
            return False
        if file_path.suffix.lower() not in self.allowed_extensions:
            return False
        return True
    
    def parse_csv(self, content: str) -> List[BatchItem]:
        """
        Parse CSV content into batch items.
        
        Expected CSV format:
            file_path,options
            /path/to/file1.jpg,{"top_k": 5}
            /path/to/file2.jpg,
        
        Args:
            content: CSV file content
        
        Returns:
            List of BatchItem
        """
        items = []
        reader = csv.DictReader(content.splitlines())
        
        for idx, row in enumerate(reader):
            if idx >= self.max_items:
                logger.warning(f"Batch limit reached ({self.max_items}), truncating")
                break
            
            file_path = row.get("file_path", "").strip()
            if not file_path:
                continue
            
            # Parse options JSON if present
            options_str = row.get("options", "").strip()
            options = {}
            if options_str:
                try:
                    options = json.loads(options_str)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in options for row {idx}: {options_str}")
            
            items.append(BatchItem(
                index=idx,
                file_path=file_path,
                options={**self.default_options, **options},
            ))
        
        return items
    
    def scan_folder(
        self,
        folder_path: Path,
        recursive: bool = False,
        file_pattern: Optional[str] = None,
    ) -> List[BatchItem]:
        """
        Scan folder for files to process.
        
        Args:
            folder_path: Path to folder
            recursive: Whether to scan subdirectories
            file_pattern: Optional glob pattern (e.g., "*.jpg")
        
        Returns:
            List of BatchItem
        """
        if not folder_path.exists() or not folder_path.is_dir():
            raise ValueError(f"Folder not found: {folder_path}")
        
        items = []
        pattern = file_pattern or "*"
        
        if recursive:
            files = folder_path.rglob(pattern)
        else:
            files = folder_path.glob(pattern)
        
        for idx, file_path in enumerate(sorted(files)):
            if idx >= self.max_items:
                logger.warning(f"Batch limit reached ({self.max_items}), truncating")
                break
            
            if not self.validate_file(file_path):
                continue
            
            items.append(BatchItem(
                index=idx,
                file_path=str(file_path),
                options=self.default_options.copy(),
            ))
        
        return items
    
    async def process_batch(
        self,
        batch_id: str,
        items: List[BatchItem],
        session: Any,
    ) -> BatchResult:
        """
        Process a batch of items.
        
        Args:
            batch_id: Unique batch identifier
            items: List of items to process
            session: Database session
        
        Returns:
            BatchResult with job IDs
        """
        result = BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            items=items,
            status=BatchStatus.PROCESSING,
        )
        self._batches[batch_id] = result
        
        for item in items:
            try:
                file_path = Path(item.file_path)
                
                if not self.validate_file(file_path):
                    item.status = "error"
                    item.error = f"Invalid file: {item.file_path}"
                    result.failed += 1
                    continue
                
                job_id = await self.create_job(file_path, item.options, session)
                item.job_id = job_id
                item.status = "created"
                result.successful += 1
                
            except Exception as e:
                logger.error(f"Failed to create job for {item.file_path}: {e}")
                item.status = "error"
                item.error = str(e)
                result.failed += 1
                result.errors.append(f"Item {item.index}: {e}")
            
            result.processed += 1
        
        # Set final status
        if result.failed == 0:
            result.status = BatchStatus.COMPLETED
        elif result.successful == 0:
            result.status = BatchStatus.FAILED
        else:
            result.status = BatchStatus.PARTIAL
        
        return result
    
    def get_batch_status(self, batch_id: str) -> Optional[BatchResult]:
        """Get status of a batch."""
        return self._batches.get(batch_id)
    
    def create_router(self, get_session: Callable) -> APIRouter:
        """
        Create FastAPI router for batch endpoints.
        
        Args:
            get_session: Dependency for getting database session
        
        Returns:
            FastAPI router with batch endpoints
        """
        router = APIRouter()
        
        @router.post("/csv", response_model=BatchImportResponse)
        async def import_from_csv(
            background_tasks: BackgroundTasks,
            file: UploadFile = File(...),
            options: Optional[str] = Form(None),
            session = Depends(get_session),
        ):
            """
            Import batch from CSV file.
            
            CSV format:
            ```
            file_path,options
            /path/to/file1.jpg,{"top_k": 5}
            /path/to/file2.jpg,
            ```
            """
            import uuid
            
            # Parse CSV content
            content = (await file.read()).decode("utf-8")
            items = self.parse_csv(content)
            
            if not items:
                raise HTTPException(status_code=400, detail="No valid items found in CSV")
            
            if len(items) > self.max_items:
                raise HTTPException(
                    status_code=400,
                    detail=f"Too many items ({len(items)}), max is {self.max_items}"
                )
            
            # Apply global options if provided
            if options:
                try:
                    global_opts = json.loads(options)
                    for item in items:
                        item.options = {**global_opts, **item.options}
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid JSON in options")
            
            batch_id = str(uuid.uuid4())
            
            # Process in background
            background_tasks.add_task(
                self.process_batch,
                batch_id,
                items,
                session,
            )
            
            return BatchImportResponse(
                batch_id=batch_id,
                total_items=len(items),
                status="processing",
                message=f"Processing {len(items)} items",
            )
        
        @router.post("/folder", response_model=BatchImportResponse)
        async def import_from_folder(
            request: BatchImportRequest,
            background_tasks: BackgroundTasks,
            session = Depends(get_session),
        ):
            """Import batch from server folder."""
            import uuid
            
            folder_path = Path(request.folder_path)
            
            if not folder_path.exists():
                raise HTTPException(status_code=404, detail=f"Folder not found: {request.folder_path}")
            
            if not folder_path.is_dir():
                raise HTTPException(status_code=400, detail=f"Not a directory: {request.folder_path}")
            
            # Scan folder
            items = self.scan_folder(
                folder_path,
                recursive=request.recursive,
                file_pattern=request.file_pattern,
            )
            
            if not items:
                raise HTTPException(status_code=400, detail="No valid files found in folder")
            
            # Apply options
            if request.options:
                for item in items:
                    item.options = {**request.options, **item.options}
            
            batch_id = str(uuid.uuid4())
            
            # Process in background
            background_tasks.add_task(
                self.process_batch,
                batch_id,
                items,
                session,
            )
            
            return BatchImportResponse(
                batch_id=batch_id,
                total_items=len(items),
                status="processing",
                message=f"Processing {len(items)} items from {request.folder_path}",
            )
        
        @router.get("/{batch_id}", response_model=BatchStatusResponse)
        async def get_batch_status(batch_id: str):
            """Get batch processing status."""
            batch = self.get_batch_status(batch_id)
            
            if not batch:
                raise HTTPException(status_code=404, detail="Batch not found")
            
            return BatchStatusResponse(
                batch_id=batch.batch_id,
                total_items=batch.total_items,
                processed=batch.processed,
                successful=batch.successful,
                failed=batch.failed,
                status=batch.status.value,
                job_ids=[str(item.job_id) for item in batch.items if item.job_id],
            )
        
        return router
