import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


class CloudScaleException(Exception):
    """Base exception class for all CloudScale Commerce domain errors."""

    def __init__(self, message: str, code: str = "INTERNAL_SERVER_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(CloudScaleException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str, code: str = "NOT_FOUND"):
        super().__init__(message, code, status.HTTP_404_NOT_FOUND)


class ConflictException(CloudScaleException):
    """Raised when a resource state conflict occurs (e.g., duplicate entries)."""

    def __init__(self, message: str, code: str = "CONFLICT"):
        super().__init__(message, code, status.HTTP_409_CONFLICT)


class UnauthorizedException(CloudScaleException):
    """Raised when authentication credentials are invalid or missing."""

    def __init__(self, message: str, code: str = "UNAUTHORIZED"):
        super().__init__(message, code, status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(CloudScaleException):
    """Raised when the user has insufficient permissions to perform an action."""

    def __init__(self, message: str, code: str = "FORBIDDEN"):
        super().__init__(message, code, status.HTTP_403_FORBIDDEN)


class ValidationException(CloudScaleException):
    """Raised when business logic validation fails."""

    def __init__(self, message: str, code: str = "VALIDATION_FAILED"):
        super().__init__(message, code, status.HTTP_400_BAD_REQUEST)


def setup_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers for FastAPI applications."""

    @app.exception_handler(CloudScaleException)
    async def cloudscale_exception_handler(request: Request, exc: CloudScaleException):
        correlation_id = structlog.contextvars.get_contextvars().get("correlation_id", "unknown")
        logger.warn(
            "Domain exception occurred",
            code=exc.code,
            status_code=exc.status_code,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "correlation_id": correlation_id}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        correlation_id = structlog.contextvars.get_contextvars().get("correlation_id", "unknown")
        # Format FastAPI validation errors
        errors = []
        for error in exc.errors():
            loc = ".".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg")
            errors.append(f"'{loc}': {msg}")

        message = "; ".join(errors)
        logger.warn("Request validation failed", status_code=400, errors=errors, path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": "VALIDATION_ERROR", "message": message, "correlation_id": correlation_id}},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        correlation_id = structlog.contextvars.get_contextvars().get("correlation_id", "unknown")
        logger.exception("Unhandled system exception occurred", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact support.",
                    "correlation_id": correlation_id,
                }
            },
        )
