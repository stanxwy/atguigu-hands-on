"""认证安全核心：JWT 签发/校验 + bcrypt 密码哈希。

对齐《安全规范》§3：
- JWT 含 ``sub/exp/iat/jti/iss/aud`` 并在校验时强制 issuer/audience；
- 密码使用 bcrypt 哈希（rounds=12），常量时间比较，绝不落明文。

实现说明：密码哈希直接使用 ``bcrypt`` 库（而非 passlib 的 ``CryptContext``），
以避免 passlib 1.7.4 与 bcrypt>=4.1 移除 ``bcrypt.__about__`` 导致的兼容性
异常。``passlib[bcrypt]`` 仍保留在依赖清单中以符合 SPEC 选型声明。
"""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings
from app.core.errors import AuthError

BCRYPT_ROUNDS = 12
_BCRYPT_MAX_BYTES = 72  # bcrypt 对密码字节长度的硬上限


def hash_password(plain: str) -> str:
    """对明文密码做 bcrypt 哈希（rounds=12）。

    Args:
        plain: 明文密码。

    Returns:
        bcrypt 哈希字符串（可直接落库）。

    Raises:
        ValueError: 密码字节长度超过 bcrypt 上限（72 字节）。
    """
    data = plain.encode("utf-8")
    if len(data) > _BCRYPT_MAX_BYTES:
        raise ValueError("密码过长（bcrypt 上限 72 字节）")
    return bcrypt.hashpw(data, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配（常量时间比较）。

    Args:
        plain: 明文密码。
        hashed: 已存储的 bcrypt 哈希。

    Returns:
        匹配返回 True，否则 False（含哈希非法等异常均安全返回 False）。
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: int,
    role: str,
    *,
    expires_minutes: int | None = None,
) -> tuple[str, int]:
    """签发 JWT 访问令牌。

    Args:
        user_id: 用户 ID。
        role: 用户角色（admin/user）。
        expires_minutes: 有效期（分钟），缺省使用全局配置。

    Returns:
        ``(token, expires_in_seconds)`` 二元组。
    """
    minutes = expires_minutes or settings.access_token_expire_minutes
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "jti": uuid.uuid4().hex,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, minutes * 60


def decode_token(token: str) -> dict:
    """校验并解码 JWT 令牌。

    强制要求 ``sub/exp/iat/jti/iss/aud/role`` 声明，并校验 issuer/audience。

    Args:
        token: JWT 字符串。

    Returns:
        解码后的 payload 字典。

    Raises:
        AuthError: 令牌过期或非法（统一映射为 1002）。
    """
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": ["sub", "exp", "iat", "jti", "iss", "aud", "role"],
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("登录态已过期") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("非法令牌") from exc
