"""Unified response envelope (SPEC §8) and domain-error translation.

Success responses use ``{code: 0, message: "ok", data: ...}``. Domain errors
are mapped to ``{code: <errno>, message, detail}`` with the matching HTTP
status by the registered exception handler.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions import DomainError


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    """Build a unified success envelope.

    Args:
        data: Payload to place under ``data`` (default ``None``).
        message: Optional human-readable message (default ``"ok"``).

    Returns:
        A dict ready for FastAPI to serialize: ``{code, message, data}``.
    """
    return {"code": 0, "message": message, "data": data}


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Translate a :class:`DomainError` into the unified error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate a Pydantic ``RequestValidationError`` (HTTP 422) into the
    unified error envelope (SPEC §8)."""
    return JSONResponse(
        status_code=422,
        content={
            "code": 42200,
            "message": "请求参数校验失败",
            "detail": str(exc.errors()),
        },
    )
