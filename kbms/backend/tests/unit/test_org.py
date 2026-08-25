"""T02 组织架构测试（SPEC §3.1 / §8）：OrgService 业务 + HTTP 集成。

覆盖：
1. OrgService：部门树/删除含子部门拒绝、用户 CRUD、角色 CRUD
2. HTTP 层：login/me、部门树、用户 CRUD 分页、角色 + 权限、统一响应包
   （成功 code:0；401/403/422 的 {code,message,detail} 结构）
"""

from __future__ import annotations

import pytest

from app.domain.exceptions import ConflictError


# --------------------------------------------------------------------------- #
# OrgService 单元测试
# --------------------------------------------------------------------------- #
def test_department_tree_nested(org_service, identity_repo):
    parent = identity_repo.create_department(name="总部", sort_order=0)
    identity_repo.create_department(name="研发部", parent_id=parent.id, sort_order=1)
    identity_repo.create_department(name="财务部", parent_id=parent.id, sort_order=2)

    tree = org_service.list_departments_tree()
    assert len(tree) == 1
    root = tree[0]
    assert root["name"] == "总部"
    assert [c["name"] for c in root["children"]] == ["研发部", "财务部"]


def test_delete_department_with_children_rejected(org_service, identity_repo):
    parent = identity_repo.create_department(name="总部")
    child = identity_repo.create_department(name="研发部", parent_id=parent.id)

    with pytest.raises(ConflictError):
        org_service.delete_department(parent.id)

    org_service.delete_department(child.id)  # 删除子部门成功


def test_create_user_duplicate_username_conflict(org_service, identity_repo):
    identity_repo.create_user("alice", "h", "Alice")
    with pytest.raises(ConflictError):
        org_service.create_user(username="alice", password="x", display_name="Alice2")


def test_create_role_duplicate_code_conflict(org_service, identity_repo):
    identity_repo.create_role("管理员", "sys_admin", "")
    with pytest.raises(ConflictError):
        org_service.create_role(role_name="另一个", role_code="sys_admin")


# --------------------------------------------------------------------------- #
# HTTP 层（FastAPI TestClient + 内存 SQLite）
# --------------------------------------------------------------------------- #
def test_login_success_envelope(client, seed_admin):
    resp = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    data = body["data"]
    assert data["access_token"]
    assert data["user_info"]["username"] == "admin"
    assert data["user_info"]["roles"] == ["sys_admin"]
    assert isinstance(data["permissions"], list)
    assert len(data["permissions"]) >= 7


def test_login_wrong_password_401_envelope(client, seed_admin):
    resp = client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 40100
    assert body["message"] == "用户名或密码错误"
    assert "detail" in body


def test_me_with_valid_token(client, admin_headers):
    resp = client.get("/api/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "admin"
    assert data["roles"] == ["sys_admin"]
    assert isinstance(data["permissions"], list)


def test_me_without_token_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 40100
    assert "detail" in body


def test_me_with_bad_token_401(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.value"})
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_departments_tree_via_http(client, admin_headers):
    parent = client.post(
        "/api/org/departments", json={"name": "总部", "sort_order": 0}, headers=admin_headers
    )
    assert parent.status_code == 200
    parent_id = parent.json()["data"]["id"]

    child = client.post(
        "/api/org/departments",
        json={"name": "研发部", "parent_id": parent_id, "sort_order": 1},
        headers=admin_headers,
    )
    assert child.status_code == 200
    child_id = child.json()["data"]["id"]

    resp = client.get("/api/org/departments", headers=admin_headers)
    assert resp.status_code == 200
    tree = resp.json()["data"]
    assert len(tree) == 1
    assert tree[0]["name"] == "总部"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["name"] == "研发部"
    assert tree[0]["children"][0]["id"] == child_id


def test_create_user_via_http(client, admin_headers):
    resp = client.post(
        "/api/org/users",
        json={"username": "alice", "password": "alice123", "display_name": "Alice"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "alice"
    assert data["display_name"] == "Alice"
    assert data["status"] == 1


def test_list_users_pagination_via_http(client, admin_headers):
    # 注意：admin_headers 依赖 seed_admin，admin 本身也是一个用户。
    for i in range(3):
        r = client.post(
            "/api/org/users",
            json={"username": f"u{i}", "password": "p123", "display_name": f"User{i}"},
            headers=admin_headers,
        )
        assert r.status_code == 200

    resp = client.get(
        "/api/org/users", params={"page": 1, "page_size": 2}, headers=admin_headers
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["total"] == 4  # admin + u0 + u1 + u2
    assert len(body["items"]) == 2

    # keyword 过滤
    resp2 = client.get("/api/org/users", params={"keyword": "u1"}, headers=admin_headers)
    assert resp2.json()["data"]["total"] == 1
    assert resp2.json()["data"]["items"][0]["username"] == "u1"


def test_update_user_via_http(client, admin_headers):
    created = client.post(
        "/api/org/users",
        json={"username": "bob", "password": "bob123", "display_name": "Bob"},
        headers=admin_headers,
    ).json()["data"]

    resp = client.put(
        f"/api/org/users/{created['id']}",
        json={"display_name": "Bob Updated"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["display_name"] == "Bob Updated"
    assert data["username"] == "bob"


def test_delete_user_via_http(client, admin_headers):
    created = client.post(
        "/api/org/users",
        json={"username": "carol", "password": "c123", "display_name": "Carol"},
        headers=admin_headers,
    ).json()["data"]

    resp = client.delete(f"/api/org/users/{created['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    lst = client.get("/api/org/users", headers=admin_headers).json()["data"]
    assert lst["total"] == 1  # 仅剩 admin


def test_roles_crud_via_http(client, admin_headers):
    created = client.post(
        "/api/org/roles",
        json={"role_name": "编辑", "role_code": "editor", "description": "编辑角色"},
        headers=admin_headers,
    )
    assert created.status_code == 200
    role_id = created.json()["data"]["id"]
    assert created.json()["data"]["role_code"] == "editor"

    # 批量覆盖权限
    perm = client.post(
        f"/api/org/roles/{role_id}/permissions",
        json={"permissions": [{"permission_code": "knowledge:unit", "permission_type": "read"}]},
        headers=admin_headers,
    )
    assert perm.status_code == 200

    roles = client.get("/api/org/roles", headers=admin_headers).json()["data"]
    editor = next(r for r in roles if r["role_code"] == "editor")
    assert editor["permissions"] == [
        {"permission_code": "knowledge:unit", "permission_type": "read"}
    ]


def test_department_crud_and_delete_with_children_rejected_via_http(client, admin_headers):
    parent = client.post(
        "/api/org/departments", json={"name": "总部"}, headers=admin_headers
    ).json()["data"]
    child = client.post(
        "/api/org/departments",
        json={"name": "研发部", "parent_id": parent["id"]},
        headers=admin_headers,
    ).json()["data"]

    # 更新部门
    upd = client.put(
        f"/api/org/departments/{child['id']}", json={"name": "研发一部"}, headers=admin_headers
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["name"] == "研发一部"

    # 删除含子部门的父部门 → 409 拒绝
    del_parent = client.delete(f"/api/org/departments/{parent['id']}", headers=admin_headers)
    assert del_parent.status_code == 409
    assert del_parent.json()["code"] == 40900

    # 先删子部门，再删父部门
    assert (
        client.delete(f"/api/org/departments/{child['id']}", headers=admin_headers).status_code
        == 200
    )
    assert (
        client.delete(f"/api/org/departments/{parent['id']}", headers=admin_headers).status_code
        == 200
    )


def test_unauthorized_401_envelope(client):
    resp = client.get("/api/org/users")  # 无 token
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 40100
    assert body["message"]
    assert "detail" in body


def test_forbidden_403_envelope(client, identity_repo, password_hasher, auth_service):
    role = identity_repo.create_role("空角色", "empty", "")
    identity_repo.create_user("noperm", password_hasher.hash("n123"), "NoPerm", role_ids=[role.id])
    token = auth_service.login("noperm", "n123").access_token

    resp = client.get("/api/org/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == 40300
    assert "detail" in body


def test_validation_422_unified_envelope(client):
    """参数校验失败应返回 {code, message, detail} 结构（SPEC §8 统一响应包）。"""
    resp = client.post("/api/auth/login", json={"username": "", "password": ""})
    assert resp.status_code == 422
    body = resp.json()
    assert set(body.keys()) >= {"code", "message", "detail"}
