"""
Custom exceptions and centralized error handling for RTO Autopilot.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
from typing import Any, Dict, Optional
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rto_autopilot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class RTOAutopilotError(Exception):
    """Base exception for RTO Autopilot application errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(RTOAutopilotError):
    """Exception raised for authentication failures."""
    pass


class AuthorizationError(RTOAutopilotError):
    """Exception raised for authorization failures."""
    pass


class DataNotFoundError(RTOAutopilotError):
    """Exception raised when requested data is not found."""
    pass


class ValidationError(RTOAutopilotError):
    """Exception raised for data validation errors."""
    pass


def get_request_context(request: Request) -> Dict[str, Any]:
    """
    Extract useful context from the request for logging.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Dictionary with context information
    """
    context = {
        "timestamp": datetime.utcnow().isoformat(),
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "client_host": request.client.host if request.client else "unknown",
    }
    
    # Add user information if available
    if hasattr(request, "session"):
        staff_id = request.session.get("staff_id")
        staff_email = request.session.get("staff_email")
        office_id = request.session.get("office_id")
        office_name = request.session.get("office_name")
        
        if staff_id:
            context["staff_id"] = staff_id
        if staff_email:
            context["staff_email"] = staff_email
        if office_id:
            context["office_id"] = office_id
        if office_name:
            context["office_name"] = office_name
    
    return context


async def rto_autopilot_exception_handler(request: Request, exc: RTOAutopilotError) -> JSONResponse:
    """
    Handle custom RTO Autopilot exceptions.
    
    Args:
        request: FastAPI request object
        exc: RTOAutopilot exception
        
    Returns:
        JSONResponse with error details
    """
    context = get_request_context(request)
    
    # Log the error with context
    logger.error(
        f"RTO Autopilot Error: {exc.message}",
        extra={
            "error_type": type(exc).__name__,
            "error_message": exc.message,
            "error_details": exc.details,
            "request_context": context
        }
    )
    
    # Return user-friendly error response
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.message,
            "type": type(exc).__name__,
            "details": exc.details
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with enhanced logging.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
        
    Returns:
        JSONResponse with error details
    """
    context = get_request_context(request)
    
    # Log the HTTP error with context
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "error_detail": exc.detail,
            "request_context": context
        }
    )
    
    # Return appropriate error response
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors.
    
    Args:
        request: FastAPI request object
        exc: Request validation exception
        
    Returns:
        JSONResponse with validation error details
    """
    context = get_request_context(request)
    
    # Log validation error with context
    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={
            "validation_errors": exc.errors(),
            "request_context": context
        }
    )
    
    # Return validation error details
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors()
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with detailed logging.
    
    Args:
        request: FastAPI request object
        exc: Unexpected exception
        
    Returns:
        JSONResponse with generic error message
    """
    context = get_request_context(request)
    
    # Log the full error with traceback
    logger.error(
        f"Unexpected Error: {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
            "request_context": context
        }
    )
    
    # Return generic error message to avoid exposing internals
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred. Please try again later.",
            "type": "InternalServerError"
        }
    )


def setup_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(RTOAutopilotError, rto_autopilot_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
