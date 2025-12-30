"""
Standardized error response module for LMSilo services.

Provides consistent error formatting and exception handlers for FastAPI.
"""

import logging
import traceback
from typing import Optional, Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """
    Standardized error response format.
    
    All API errors should return this format for consistency.
    """
    error: str  # Error type/code (e.g., "validation_error", "not_found")
    code: str   # Machine-readable error code (e.g., "ERR_VALIDATION")
    message: str  # Human-readable message
    details: Optional[dict] = None  # Additional context
    request_id: Optional[str] = None  # For tracing


class LMSiloException(Exception):
    """
    Base exception for LMSilo services.
    
    Subclass for specific error types.
    """
    
    def __init__(
        self,
        message: str,
        code: str = "ERR_INTERNAL",
        status_code: int = 500,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(LMSiloException):
    """Resource not found."""
    
    def __init__(self, resource: str, resource_id: Any, details: Optional[dict] = None):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            code="ERR_NOT_FOUND",
            status_code=404,
            details=details or {"resource": resource, "id": str(resource_id)},
        )


class ValidationError(LMSiloException):
    """Request validation failed."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="ERR_VALIDATION",
            status_code=422,
            details=details,
        )


class ConflictError(LMSiloException):
    """Resource conflict (e.g., duplicate)."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code="ERR_CONFLICT",
            status_code=409,
            details=details,
        )


class ServiceUnavailableError(LMSiloException):
    """Service temporarily unavailable (e.g., model loading)."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, details: Optional[dict] = None):
        combined_details = details or {}
        if retry_after:
            combined_details["retry_after"] = retry_after
        super().__init__(
            message=message,
            code="ERR_SERVICE_UNAVAILABLE",
            status_code=503,
            details=combined_details,
        )


class ModelLoadError(LMSiloException):
    """ML model failed to load."""
    
    def __init__(self, model_name: str, reason: str, details: Optional[dict] = None):
        super().__init__(
            message=f"Failed to load model '{model_name}': {reason}",
            code="ERR_MODEL_LOAD",
            status_code=503,
            details=details or {"model": model_name, "reason": reason},
        )


class QuotaExceededError(LMSiloException):
    """Resource quota exceeded."""
    
    def __init__(self, resource: str, limit: int, details: Optional[dict] = None):
        super().__init__(
            message=f"{resource} quota exceeded. Limit: {limit}",
            code="ERR_QUOTA_EXCEEDED",
            status_code=429,
            details=details or {"resource": resource, "limit": limit},
        )


def create_error_response(
    error: str,
    code: str,
    message: str,
    status_code: int,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error: Error type
        code: Machine-readable code
        message: Human-readable message
        status_code: HTTP status code
        details: Additional context
        request: FastAPI request for request_id
    
    Returns:
        JSONResponse with error body
    """
    request_id = None
    if request:
        # Check for existing request ID (from middleware or header)
        request_id = request.headers.get("x-request-id") or str(uuid4())
    
    response = ErrorResponse(
        error=error,
        code=code,
        message=message,
        details=details,
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(exclude_none=True),
    )


async def lmsilo_exception_handler(request: Request, exc: LMSiloException) -> JSONResponse:
    """Handler for LMSilo custom exceptions."""
    logger.warning(f"LMSiloException: {exc.code} - {exc.message}")
    
    return create_error_response(
        error=exc.code.replace("ERR_", "").lower(),
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request=request,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handler for standard HTTP exceptions."""
    error_map = {
        400: ("bad_request", "ERR_BAD_REQUEST"),
        401: ("unauthorized", "ERR_UNAUTHORIZED"),
        403: ("forbidden", "ERR_FORBIDDEN"),
        404: ("not_found", "ERR_NOT_FOUND"),
        405: ("method_not_allowed", "ERR_METHOD_NOT_ALLOWED"),
        408: ("request_timeout", "ERR_TIMEOUT"),
        429: ("too_many_requests", "ERR_RATE_LIMITED"),
        500: ("internal_error", "ERR_INTERNAL"),
        502: ("bad_gateway", "ERR_BAD_GATEWAY"),
        503: ("service_unavailable", "ERR_SERVICE_UNAVAILABLE"),
    }
    
    error, code = error_map.get(exc.status_code, ("error", "ERR_UNKNOWN"))
    
    return create_error_response(
        error=error,
        code=code,
        message=str(exc.detail) if exc.detail else f"HTTP {exc.status_code}",
        status_code=exc.status_code,
        request=request,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for Pydantic validation errors."""
    errors = exc.errors()
    
    # Format validation errors
    formatted_errors = []
    for error in errors:
        loc = " -> ".join(str(l) for l in error.get("loc", []))
        formatted_errors.append({
            "field": loc,
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        })
    
    return create_error_response(
        error="validation_error",
        code="ERR_VALIDATION",
        message="Request validation failed",
        status_code=422,
        details={"errors": formatted_errors},
        request=request,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions."""
    # Generate request ID
    request_id = request.headers.get("x-request-id") or str(uuid4())
    
    # Log full traceback
    logger.error(
        f"Unhandled exception [request_id={request_id}]: {type(exc).__name__}: {exc}",
        exc_info=True,
    )
    
    # Don't expose internal details in production
    return create_error_response(
        error="internal_error",
        code="ERR_INTERNAL",
        message="An unexpected error occurred",
        status_code=500,
        details={"request_id": request_id},
        request=request,
    )


def register_error_handlers(app: FastAPI):
    """
    Register all error handlers on a FastAPI app.
    
    Usage:
        from shared.api.errors import register_error_handlers
        
        app = FastAPI()
        register_error_handlers(app)
    """
    app.add_exception_handler(LMSiloException, lmsilo_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Registered LMSilo error handlers")


# Export common response schemas for OpenAPI documentation
error_responses = {
    400: {"model": ErrorResponse, "description": "Bad request"},
    401: {"model": ErrorResponse, "description": "Unauthorized"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    429: {"model": ErrorResponse, "description": "Rate limited"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
    503: {"model": ErrorResponse, "description": "Service unavailable"},
}
