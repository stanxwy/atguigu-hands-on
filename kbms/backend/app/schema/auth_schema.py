"""Pydantic request/response models for auth endpoints (SPEC §3.1)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Request body for ``POST /api/auth/login``."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, max_length=64, description="登录用户名")
    password: str = Field(..., min_length=1, max_length=128, description="明文密码（仅用于校验，不落日志）")


class PermissionItem(BaseModel):
    """A single ``(permission_code, permission_type)`` grant (SPEC §3.1)."""

    permission_code: str = Field(..., description="资源/菜单标识，如 knowledge:unit")
    permission_type: str = Field(..., description="操作类型：create/read/update/delete/ai_access")


class DepartmentInfo(BaseModel):
    """Lightweight department reference embedded in user payloads."""

    id: str
    name: str


class UserInfo(BaseModel):
    """Canonical user payload (SPEC §3.1 ``user_info``)."""

    id: str
    username: str
    display_name: str
    department: DepartmentInfo | None = None
    roles: list[str] = Field(default_factory=list)


class LoginData(BaseModel):
    """``data`` payload for ``POST /api/auth/login`` (SPEC §3.1)."""

    access_token: str
    user_info: UserInfo
    permissions: list[PermissionItem] = Field(default_factory=list)
