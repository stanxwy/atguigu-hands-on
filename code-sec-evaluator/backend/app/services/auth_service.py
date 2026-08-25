"""认证服务：管理员初始化 + 登录。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AlreadyInitializedError, AuthError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


async def init_admin(db: AsyncSession, username: str, password: str) -> User:
    """初始化首个管理员账户（仅当不存在 admin 时可调用）。

    Args:
        db: 数据库会话。
        username: 管理员用户名。
        password: 明文密码（仅用于哈希，不落库）。

    Returns:
        新建的 User 实例（尚未 commit，由调用方提交）。

    Raises:
        AlreadyInitializedError: 已存在 admin 用户（1004）。
    """
    existing = await db.scalar(select(User).where(User.role == "admin"))
    if existing is not None:
        raise AlreadyInitializedError()
    user = User(
        username=username,
        password_hash=hash_password(password),
        role="admin",
        status="active",
    )
    db.add(user)
    await db.flush()
    return user


async def login(db: AsyncSession, username: str, password: str) -> dict[str, Any]:
    """校验用户名密码并签发 JWT。

    登录失败统一返回「用户名或密码错误」，不区分用户是否存在（防枚举，安全规范 §3.3.2）。

    Args:
        db: 数据库会话。
        username: 用户名。
        password: 明文密码。

    Returns:
        登录数据（access_token/token_type/expires_in/user）。

    Raises:
        AuthError: 用户名或密码错误（1002）。
    """
    user = await db.scalar(select(User).where(User.username == username))
    if user is None or user.status != "active":
        raise AuthError("用户名或密码错误")
    if not verify_password(password, user.password_hash):
        raise AuthError("用户名或密码错误")
    token, expires_in = create_access_token(user.id, user.role)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }
