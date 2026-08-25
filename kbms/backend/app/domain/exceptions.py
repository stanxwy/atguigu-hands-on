"""Domain-level error types shared across the service layer (SPEC §8).

Services and API middleware raise these plain exceptions (no web-framework
dependency); the API layer translates them into the unified response envelope
``{code, message, detail}`` with the matching HTTP status (see
``app/api/responses.py``).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base error carrying an HTTP status and an application errno."""

    def __init__(
        self,
        status_code: int,
        code: int,
        message: str,
        detail: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class BadRequestError(DomainError):
    """HTTP 400 — malformed or invalid request semantics."""

    def __init__(self, message: str = "请求参数错误", detail: str | None = None) -> None:
        super().__init__(400, 40000, message, detail)


class UnauthorizedError(DomainError):
    """HTTP 401 — missing/invalid/expired credentials."""

    def __init__(self, message: str = "未认证或登录已过期", detail: str | None = None) -> None:
        super().__init__(401, 40100, message, detail)


class ForbiddenError(DomainError):
    """HTTP 403 — authenticated but lacking the required permission."""

    def __init__(self, message: str = "没有操作权限", detail: str | None = None) -> None:
        super().__init__(403, 40300, message, detail)


class NotFoundError(DomainError):
    """HTTP 404 — target resource does not exist."""

    def __init__(self, message: str = "资源不存在", detail: str | None = None) -> None:
        super().__init__(404, 40400, message, detail)


class ConflictError(DomainError):
    """HTTP 409 — conflicts with existing state (e.g. duplicate username)."""

    def __init__(self, message: str = "资源冲突", detail: str | None = None) -> None:
        super().__init__(409, 40900, message, detail)
