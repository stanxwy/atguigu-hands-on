"""Organization endpoints (SPEC §3.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_org_service
from app.api.middleware.auth import CurrentUser, get_current_user
from app.api.middleware.rbac import require_permission
from app.api.responses import ok
from app.schema.org_schema import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
    RoleCreateRequest,
    RolePermissionsRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.services.org_service import OrgService

router = APIRouter(prefix="/org", tags=["org"])


@router.get(
    "/departments",
    summary="部门树",
    description="返回完整部门树（根节点优先，children 递归嵌套），对应 SPEC §3.1。",
)
def list_departments(
    current_user: CurrentUser = Depends(get_current_user),
    service: OrgService = Depends(get_org_service),
):
    return ok(service.list_departments_tree())


@router.get(
    "/users",
    summary="用户列表",
    description="按关键字/部门分页查询用户（辅助接口）。",
)
def list_users(
    keyword: str | None = Query(default=None),
    department_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: CurrentUser = Depends(require_permission("org:user", "read")),
    service: OrgService = Depends(get_org_service),
):
    return ok(
        service.list_users(
            keyword=keyword, department_id=department_id, page=page, page_size=page_size
        )
    )


@router.post(
    "/users",
    summary="创建用户",
    description="创建用户并（可选）绑定角色，密码 bcrypt 加盐存储。",
)
def create_user(
    req: UserCreateRequest,
    _: CurrentUser = Depends(require_permission("org:user", "create")),
    service: OrgService = Depends(get_org_service),
):
    return ok(
        service.create_user(
            username=req.username,
            password=req.password,
            display_name=req.display_name,
            department_id=req.department_id,
            role_ids=req.role_ids,
            status=req.status,
        )
    )


@router.put(
    "/users/{user_id}",
    summary="更新用户",
    description="更新用户（密码可选；提供 role_ids 时整体覆盖角色绑定）。",
)
def update_user(
    user_id: str,
    req: UserUpdateRequest,
    _: CurrentUser = Depends(require_permission("org:user", "update")),
    service: OrgService = Depends(get_org_service),
):
    return ok(
        service.update_user(
            user_id,
            password=req.password,
            display_name=req.display_name,
            department_id=req.department_id,
            status=req.status,
            role_ids=req.role_ids,
        )
    )


@router.delete(
    "/users/{user_id}",
    summary="删除用户",
    description="物理删除用户（部门 leader / 知识创建人 / 日志等外键由 DB 置空）。",
)
def delete_user(
    user_id: str,
    _: CurrentUser = Depends(require_permission("org:user", "delete")),
    service: OrgService = Depends(get_org_service),
):
    service.delete_user(user_id)
    return ok({})


@router.get(
    "/roles",
    summary="角色列表",
    description="返回角色及其权限列表，对应 SPEC §3.1。",
)
def list_roles(
    _: CurrentUser = Depends(require_permission("org:role", "read")),
    service: OrgService = Depends(get_org_service),
):
    return ok(service.list_roles())


@router.post(
    "/roles",
    summary="创建角色",
    description="创建角色（role_code 唯一，辅助接口）。",
)
def create_role(
    req: RoleCreateRequest,
    _: CurrentUser = Depends(require_permission("org:role", "create")),
    service: OrgService = Depends(get_org_service),
):
    return ok(
        service.create_role(
            role_name=req.role_name, role_code=req.role_code, description=req.description
        )
    )


@router.post(
    "/roles/{role_id}/permissions",
    summary="配置角色权限",
    description="事务覆盖角色的全部权限（改后即时生效，对应 SPEC §8 实时解析）。",
)
def replace_role_permissions(
    role_id: str,
    req: RolePermissionsRequest,
    _: CurrentUser = Depends(require_permission("org:role", "update")),
    service: OrgService = Depends(get_org_service),
):
    service.replace_role_permissions(
        role_id, [(p.permission_code, p.permission_type) for p in req.permissions]
    )
    return ok({})


@router.post(
    "/departments",
    summary="创建部门",
    description="创建部门（辅助接口，满足 2.9.11 AC-1「部门管理」）。",
)
def create_department(
    req: DepartmentCreateRequest,
    _: CurrentUser = Depends(require_permission("org:user", "update")),
    service: OrgService = Depends(get_org_service),
):
    return ok(
        service.create_department(
            name=req.name,
            parent_id=req.parent_id,
            leader_id=req.leader_id,
            sort_order=req.sort_order,
        )
    )


@router.put(
    "/departments/{department_id}",
    summary="更新部门",
    description="更新部门字段（辅助接口，满足 2.9.11 AC-1「部门管理」）。",
)
def update_department(
    department_id: str,
    req: DepartmentUpdateRequest,
    _: CurrentUser = Depends(require_permission("org:user", "update")),
    service: OrgService = Depends(get_org_service),
):
    return ok(
        service.update_department(
            department_id,
            name=req.name,
            parent_id=req.parent_id,
            leader_id=req.leader_id,
            sort_order=req.sort_order,
        )
    )


@router.delete(
    "/departments/{department_id}",
    summary="删除部门",
    description="删除部门（存在子部门时拒绝，辅助接口）。",
)
def delete_department(
    department_id: str,
    _: CurrentUser = Depends(require_permission("org:user", "update")),
    service: OrgService = Depends(get_org_service),
):
    service.delete_department(department_id)
    return ok({})
