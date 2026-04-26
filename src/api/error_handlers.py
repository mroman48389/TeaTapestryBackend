# Layer 1 (API/topmost layer): Contains FastAPI exception handlers for the API layer.
# These exception handlers should convert internal errors to clean HTTP responses. 
# This layer ensures the frontend always gets predictable responses. Errors to handle
# include domain, validation, a catch all for unexpected exceptions, logging hooks, and
# a consistent JSON error shape.

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from src.app.errors import (
    DomainError,
    TeaProfileNotFoundError,
    TeaProfileValidationError,
    TeaProfileConflictError,
    TeaProfileQueryError,
)

# Set up a logger for this module. __name__ will produce "src.api.error_handlers". This
# will tell us the name of the file that produced messages in logs. We can enable or
# disable them per module, filter logs by module name, and have more control over our
# log information.
logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


def _get_request_id(request: Request) -> str:
    """Use incoming X-Request-ID if present, otherwise generate a UUID."""
    header_value = request.headers.get(REQUEST_ID_HEADER)
    return header_value or str(uuid4())


def _error_response(
    *,
    request: Request,
    exc_type: str,
    message: str,
    status_code: int,
    details: Optional[Mapping[str, Any]] = None,
) -> JSONResponse:
    request_id = _get_request_id(request)
    timestamp = datetime.now(timezone.utc).isoformat()
    path = request.url.path

    # request_id:
    #     -Lets us trace a single request through logs.
    #     -Works with OpenTelemetry.
    #     -Lets frontend include the ID in bug reports.
    #     -Lets us correlate logs across services.
    #
    # timestamp: 
    #     -Helps in debugging.
    #     -Helps in log correlation.
    #     -Helps in analytics.
    #
    # path
    #     -Helps identify which endpoint failed.
    #     -Helps with routing issues.
    #     -Helps with frontend debugging.
    #
    # status
    #     -Lets frontend branch on error type.
    #     -Makes logs easier to search.

    payload: Dict[str, Any] = {
        "error": {
            "type": exc_type,
            "message": message,
            "details": details or None,
            "status": status_code,
            "path": path,
            "request_id": request_id,
            "timestamp": timestamp,
        }
    }

    # Structured log for observability
    logger.error(
        (f"API error: type={exc_type}, status={status_code}, "
         f"path={path}, request_id={request_id}, details={details}")
    )

    return JSONResponse(status_code = status_code, content = payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all API-level exception handlers on the FastAPI app."""

    @app.exception_handler(TeaProfileNotFoundError)
    async def tea_profile_not_found_handler(
        request: Request, exc: TeaProfileNotFoundError
    ) -> JSONResponse:
        
        return _error_response(
            request = request,
            exc_type = exc.__class__.__name__,
            message = exc.message,
            status_code = status.HTTP_404_NOT_FOUND,
            details = exc.details,
        )

    @app.exception_handler(TeaProfileValidationError)
    async def tea_profile_validation_handler(
        request: Request, exc: TeaProfileValidationError
    ) -> JSONResponse:
        
        return _error_response(
            request = request,
            exc_type = exc.__class__.__name__,
            message = exc.message,
            status_code = status.HTTP_400_BAD_REQUEST,
            details = exc.details,
        )

    @app.exception_handler(TeaProfileConflictError)
    async def tea_profile_conflict_handler(
        request: Request, exc: TeaProfileConflictError
    ) -> JSONResponse:
        
        return _error_response(
            request = request,
            exc_type = exc.__class__.__name__,
            message = exc.message,
            status_code = status.HTTP_409_CONFLICT,
            details = exc.details,
        )

    @app.exception_handler(TeaProfileQueryError)
    async def tea_profile_query_handler(
        request: Request, exc: TeaProfileQueryError
    ) -> JSONResponse:
        
        return _error_response(
            request = request,
            exc_type = exc.__class__.__name__,
            message = exc.message,
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            details = exc.details,
        )

    @app.exception_handler(DomainError)
    async def generic_domain_error_handler(
        request: Request, exc: DomainError
    ) -> JSONResponse:
        
        # Fallback for any DomainError not explicitly mapped above.
        return _error_response(
            request = request,
            exc_type = exc.__class__.__name__,
            message = exc.message,
            status_code = status.HTTP_400_BAD_REQUEST,
            details = exc.details,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        
        # Last-resort catch-all: never leak raw exceptions to clients.
        logger.exception("Unhandled exception", exc_info = exc)

        return _error_response(
            request = request,
            exc_type = "InternalServerError",
            message = "Internal server error",
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            details = None,
        )
