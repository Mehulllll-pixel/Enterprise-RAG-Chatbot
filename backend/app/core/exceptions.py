from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Any, Dict, Optional, Union
from app.utils.logger import logger
from app.core.config import settings

class APIException(Exception):
    """Base API Exception for structured error reporting."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

class EntityNotFoundException(APIException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="ENTITY_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )

class AuthenticationException(APIException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )

class AuthorizationException(APIException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_FAILED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )

class ConflictException(APIException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="ENTITY_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )

class ValidationException(APIException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="VALIDATION_FAILED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Catches custom APIExceptions and returns a normalized JSON structure."""
    logger.warning(f"APIException ({exc.code}): {exc.message} | Details: {exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Catches standard Pydantic validation errors and reformats them."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(map(str, error.get("loc", []))),
            "message": error.get("msg"),
            "type": error.get("type")
        })
    logger.warning(f"ValidationError on {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_FAILED",
                "message": "The request payload contains validation errors.",
                "details": errors
            }
        }
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled exceptions, logs backtrace, and returns safe 500 error."""
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}", exc_info=exc)
    import traceback
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact the administrator.",
                "details": f"{type(exc).__name__}: {str(exc)}\nTraceback:\n{tb}"
            }
        }
    )
