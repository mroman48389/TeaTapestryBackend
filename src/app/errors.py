# Layer 2 (Domain/service/middle layer): Contains custom exception handlers to express 
# meaningful business logic failures. Layer 2 will turn them into HTTP responses.
#
# Domain exceptions are expressions of semantic intent rather than behavior containers, 
# so these will generally be sparse/bare.

from __future__ import annotations

from typing import Any, Mapping, Optional


class DomainError(Exception):
    """Base class for all domain-level errors."""

    def __init__(
        self,
        message: str,
        *,
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        
        super().__init__(message)

        self.message = message
        self.details = details or {}


class TeaProfileNotFoundError(DomainError):
    """Raised when a tea profile cannot be found."""


class TeaProfileValidationError(DomainError):
    """Raised when a tea profile payload is invalid."""


class TeaProfileConflictError(DomainError):
    """Raised when a tea profile conflicts with existing data (such as a duplicate entry)."""


class TeaProfileQueryError(DomainError):
    """Raised when a query for tea profiles fails unexpectedly."""
