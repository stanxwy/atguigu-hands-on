"""Pydantic request models for organization endpoints (SPEC §3.1)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schema.auth_schema import PermissionItem


class UserCreateRequest(BaseModel):
    """Request body for ``POST /api/org/users``."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=64)
    department_id: str | None = None
    role_ids: list[str] = Field(default_factory=list)
    status: int = Field(1, ge=0, le=1, description="1 启用 / 0 禁用")


class UserUpdateRequest(BaseModel):
    """Request body for ``PUT /api/org/users/{id}`` (password optional)."""

    model_config = ConfigDict(extra="forbid")

    password: str | None = Field(None, max_length=128)
    display_name: str | None = Field(None, min_length=1, max_length=64)
    department_id: str | None = None
    role_ids: list[str] | None = None
    status: int | None = Field(None, ge=0, le=1)


class RoleCreateRequest(BaseModel):
    """Request body for ``POST /api/org/roles``."""

    model_config = ConfigDict(extra="forbid")

    role_name: str = Field(..., min_length=1, max_length=64)
    role_code: str = Field(..., min_length=1, max_length=64)
    description: str | None = Field(None, max_length=255)


class RolePermissionsRequest(BaseModel):
    """Request body for ``POST /api/org/roles/{id}/permissions`` (transaction覆盖)."""

    model_config = ConfigDict(extra="forbid")

    permissions: list[PermissionItem]


class DepartmentCreateRequest(BaseModel):
    """Request body for ``POST /api/org/departments`` (auxiliary)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=64)
    parent_id: str | None = None
    leader_id: str | None = None
    sort_order: int = 0


class DepartmentUpdateRequest(BaseModel):
    """Request body for ``PUT /api/org/departments/{id}`` (auxiliary).

    ``None`` values mean "leave unchanged".
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=64)
    parent_id: str | None = None
    leader_id: str | None = None
    sort_order: int | None = None
