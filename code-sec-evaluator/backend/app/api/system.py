"""认证与系统接口：POST /init、POST /login、GET+PUT /config。"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.errors import ok
from app.models.user import User
from app.schemas.auth import InitRequest, LoginRequest
from app.schemas.config import ConfigUpdateRequest
from app.services import auth_service, config_service

router = APIRouter(prefix="/api/system", tags=["System"])


@router.post("/init")
async def init_system(
    payload: InitRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """初始化管理员账户（仅未初始化时可调用，重复初始化返回 1004）。"""
    user = await auth_service.init_admin(db, payload.username, payload.password)
    await db.commit()
    await db.refresh(user)
    return ok({"id": user.id, "username": user.username, "role": user.role})


@router.post("/login")
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """登录：校验用户名密码并签发 JWT。"""
    data = await auth_service.login(db, payload.username, payload.password)
    return ok(data)


@router.get("/config")
async def get_config(
    _user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """查询系统配置（管理员）。"""
    return ok(await config_service.get_nested(db))


@router.put("/config")
async def update_config(
    payload: ConfigUpdateRequest,
    _user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """更新系统配置（管理员），返回被更新分组的配置片段。"""
    return ok(await config_service.update_configs(db, payload.config))
