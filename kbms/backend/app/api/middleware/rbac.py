"""Operation-permission (RBAC) dependency (SPEC §8 realtime role_permissions)."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from app.api.deps import get_identity_repo
from app.api.middleware.auth import CurrentUser, get_current_user
from app.domain.exceptions import ForbiddenError
from app.domain.ports.identity_repository import IdentityRepository


def require_permission(permission_code: str, permission_type: str) -> Callable[..., CurrentUser]:
    """Build a FastAPI dependency enforcing a single ``(code, type)`` grant.

    On every request the user's roles and ``role_permissions`` are re-read from
    the DB (never trusted from the JWT), so permission changes take effect
    immediately (SPEC §8).
    """

    def _checker(
        current_user: CurrentUser = Depends(get_current_user),
        identity_repo: IdentityRepository = Depends(get_identity_repo),
    ) -> CurrentUser:
        roles = identity_repo.get_user_roles(current_user.id)
        for role in roles:
            for perm in identity_repo.get_role_permissions(role.id):
                if (
                    perm.permission_code == permission_code
                    and perm.permission_type == permission_type
                ):
                    return current_user
        raise ForbiddenError(
            f"缺少权限 {permission_code}:{permission_type}",
            detail=f"user={current_user.id}",
        )

    return _checker
