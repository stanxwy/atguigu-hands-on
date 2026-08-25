"""Auth endpoints (SPEC §3.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service
from app.api.middleware.auth import CurrentUser, get_current_user
from app.api.responses import ok
from app.schema.auth_schema import LoginRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    summary="用户登录",
    description="校验 bcrypt 密码后签发 JWT，返回 access_token / user_info / permissions（对应 2.9.8）。",
)
def login(req: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return ok(service.login(req.username, req.password).model_dump())


@router.get(
    "/me",
    summary="当前用户信息",
    description="返回当前登录用户及其角色与扁平权限列表（辅助接口）。",
)
def me(current_user: CurrentUser = Depends(get_current_user)):
    return ok(current_user.model_dump())


@router.post(
    "/logout",
    summary="退出登录",
    description="无状态 JWT：服务端不持有会话，客户端丢弃 token 即可（可选黑名单为进阶项）。",
)
def logout(current_user: CurrentUser = Depends(get_current_user)):
    return ok({})
