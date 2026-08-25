"""T02 RBAC 测试（SPEC §8：每次请求从 DB 实时解析 role_permissions）。

覆盖：
1. require_permission 依赖：有权限放行 / 无权限 Forbidden
2. 实时鉴权：改 role_permissions 后旧 token 立即按新权限生效，不信任 JWT roles
"""

from __future__ import annotations

import pytest

from app.api.middleware.auth import CurrentUser
from app.api.middleware.rbac import require_permission
from app.domain.exceptions import ForbiddenError
from app.schema.auth_schema import PermissionItem


def _current_user(user_id: str, username: str, *, permissions=None) -> CurrentUser:
    return CurrentUser(
        id=user_id,
        username=username,
        display_name=username,
        permissions=permissions or [],
    )


def test_require_permission_granted(identity_repo):
    role = identity_repo.create_role("访客", "viewer", "")
    identity_repo.replace_role_permissions(role.id, [("org:user", "read")])
    user = identity_repo.create_user("alice", "h", "Alice", role_ids=[role.id])

    checker = require_permission("org:user", "read")
    assert checker(_current_user(user.id, "alice"), identity_repo).id == user.id


def test_require_permission_denied(identity_repo):
    role = identity_repo.create_role("访客", "viewer", "")
    user = identity_repo.create_user("alice", "h", "Alice", role_ids=[role.id])

    checker = require_permission("org:user", "read")
    with pytest.raises(ForbiddenError):
        checker(_current_user(user.id, "alice"), identity_repo)


def test_require_permission_realtime_db_change(identity_repo):
    """即使 CurrentUser 携带旧权限快照，require_permission 也只读 DB。"""
    role = identity_repo.create_role("访客", "viewer", "")
    identity_repo.replace_role_permissions(role.id, [("org:user", "read")])
    user = identity_repo.create_user("alice", "h", "Alice", role_ids=[role.id])

    current_user = _current_user(
        user.id,
        "alice",
        permissions=[PermissionItem(permission_code="org:user", permission_type="read")],
    )
    checker = require_permission("org:user", "read")
    assert checker(current_user, identity_repo).id == user.id

    # 撤销 DB 中的权限（JWT/快照中的 roles 与 permissions 均不变）
    identity_repo.replace_role_permissions(role.id, [])
    with pytest.raises(ForbiddenError):
        checker(current_user, identity_repo)


def test_rbac_realtime_old_token_reflects_db_change(
    client, identity_repo, password_hasher, auth_service
):
    """HTTP 层：改 role_permissions 后旧 token 立即按新权限鉴权。"""
    role = identity_repo.create_role("访客", "viewer", "")
    identity_repo.replace_role_permissions(role.id, [("org:user", "read")])
    identity_repo.create_user(
        "viewer", password_hasher.hash("viewer123"), "访客", role_ids=[role.id]
    )
    token = auth_service.login("viewer", "viewer123").access_token
    headers = {"Authorization": f"Bearer {token}"}

    # 有权限：放行
    assert client.get("/api/org/users", headers=headers).status_code == 200

    # 改 DB（JWT 中 roles 不变），旧 token 立即被拒绝
    identity_repo.replace_role_permissions(role.id, [])
    resp = client.get("/api/org/users", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == 40300
