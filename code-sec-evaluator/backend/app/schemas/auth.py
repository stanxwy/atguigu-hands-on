"""认证与系统接口请求/响应模型（对齐 openapi.yaml components/schemas）。"""

import re

from pydantic import ConfigDict, Field, field_validator

from app.schemas import StrictModel

# 密码强度：长度 8~64，且至少含大写/小写/数字/特殊字符中的三类（安全规范 §3.3.1）
_PWD_CATEGORY_RES = (
    re.compile(r"[a-z]"),
    re.compile(r"[A-Z]"),
    re.compile(r"[0-9]"),
    re.compile(r"[^A-Za-z0-9]"),
)


class InitRequest(StrictModel):
    """初始化管理员请求体。"""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=8, max_length=64)

    @field_validator("username")
    @classmethod
    def _no_control_chars(cls, value: str) -> str:
        if any(ord(ch) < 32 for ch in value):
            raise ValueError("username 含非法控制字符")
        return value

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        if not (8 <= len(value) <= 64):
            raise ValueError("密码长度须为 8~64 位")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码过长（bcrypt 上限 72 字节）")
        categories = sum(bool(pat.search(value)) for pat in _PWD_CATEGORY_RES)
        if categories < 3:
            raise ValueError("密码须含大写/小写/数字/特殊字符中的至少三类")
        return value

    @field_validator("password")
    @classmethod
    def _not_same_as_username(cls, value: str, info) -> str:
        username = info.data.get("username")
        if username and value == username:
            raise ValueError("密码不得与用户名相同")
        return value


class LoginRequest(StrictModel):
    """登录请求体。"""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=64)


class UserOut(StrictModel):
    """用户响应体（不含敏感字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str


class LoginData(StrictModel):
    """登录成功返回数据。"""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserOut


class InitData(StrictModel):
    """初始化成功返回数据（与 UserOut 等价）。"""

    id: int
    username: str
    role: str
