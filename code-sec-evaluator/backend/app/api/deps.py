"""依赖注入：get_db / get_current_user / require_admin / get_owned_project。

对齐《安全规范》§3.7（防 IDOR 越权）：资源接口统一经 ``get_owned_project``
校验归属，admin 接口经 ``require_admin`` 鉴权。
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ForbiddenError, NotFoundError
from app.core.security import decode_token
from app.database import async_session_factory, get_db
from app.models.project import Project
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """解析 Bearer JWT 并加载当前用户（校验状态）。"""
    if credentials is None or not credentials.credentials:
        raise AuthError()
    payload = decode_token(credentials.credentials)
    user = await db.get(User, int(payload["sub"]))
    if user is None or user.status != "active":
        raise AuthError("用户不存在或已禁用")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """要求 admin 角色（非管理员返回 1003）。"""
    if user.role != "admin":
        raise ForbiddenError("权限不足，需管理员角色")
    return user


async def get_owned_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """获取项目并校验归属（防 IDOR）。"""
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("项目不存在")
    if user.role != "admin" and project.created_by != user.id:
        raise ForbiddenError("无权访问该项目")
    return project


async def authenticate_token(token: str) -> User:
    """WebSocket 握手鉴权：解码令牌并加载用户（独立短会话）。"""
    payload = decode_token(token)
    async with async_session_factory() as db:
        user = await db.get(User, int(payload["sub"]))
        if user is None or user.status != "active":
            raise AuthError("用户不存在或已禁用")
        return user


async def check_project_access(user: User, project_id: int) -> Project:
    """校验用户对项目的访问权限（WebSocket 订阅前调用）。"""
    async with async_session_factory() as db:
        project = await db.get(Project, project_id)
        if project is None:
            raise NotFoundError("项目不存在")
        if user.role != "admin" and project.created_by != user.id:
            raise ForbiddenError("无权访问该项目")
        return project
