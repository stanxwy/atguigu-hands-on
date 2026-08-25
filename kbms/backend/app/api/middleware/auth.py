"""Bearer-token authentication dependency (SPEC §3.1 / §8)."""

from __future__ import annotations

from fastapi import Depends, Header
from pydantic import BaseModel, Field

from app.api.deps import get_auth_service
from app.domain.exceptions import UnauthorizedError
from app.schema.auth_schema import DepartmentInfo, PermissionItem
from app.services.auth_service import AuthService


class CurrentUser(BaseModel):
    """Authenticated user injected into protected endpoints."""

    id: str
    username: str
    display_name: str
    department: DepartmentInfo | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[PermissionItem] = Field(default_factory=list)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise UnauthorizedError("缺少认证令牌")
    scheme, sep, token = authorization.partition(" ")
    if sep == "" or scheme.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("认证头格式错误，应为 Bearer <token>")
    return token.strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    """Resolve the current user from the ``Authorization: Bearer <token>`` header.

    The token is verified and the user + roles + permissions are re-read from
    the database on every request.
    """
    token = _extract_bearer_token(authorization)
    data = auth_service.get_current_user_by_token(token)
    return CurrentUser(**data)
