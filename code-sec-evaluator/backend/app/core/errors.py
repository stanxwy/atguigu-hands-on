"""错误码与统一异常处理。

对齐《SPEC》§3.1.2 错误码约定与《安全规范》分层校验模型：
- ``AppError`` 为业务异常基类，携带业务码 + 默认 HTTP 状态码；
- 统一异常处理器在 ``app.main`` 中注册，将异常转为 ``{code, message, data}``。
"""

from typing import Any


class AppError(Exception):
    """业务异常基类。

    Args:
        code: 业务状态码（见错误码表）。
        message: 面向用户/调用方的状态说明。
        http_status: HTTP 状态码；缺省时按错误码映射表推导。
        data: 可选附加数据（默认 None）。
    """

    # 错误码 → 默认 HTTP 状态码映射
    DEFAULT_HTTP_STATUS: dict[int, int] = {
        1001: 400,
        1002: 401,
        1003: 403,
        1004: 409,
        2001: 404,
        2002: 409,
        3001: 500,
        5000: 500,
    }

    def __init__(
        self,
        code: int,
        message: str,
        *,
        http_status: int | None = None,
        data: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status or self.DEFAULT_HTTP_STATUS.get(code, 500)
        self.data = data

    def as_dict(self) -> dict[str, Any]:
        """序列化为统一响应体。"""
        return {"code": self.code, "message": self.message, "data": self.data}


class ParamError(AppError):
    """参数校验失败（1001）。"""

    def __init__(self, message: str = "参数校验失败", data: Any = None) -> None:
        super().__init__(1001, message, data=data)


class AuthError(AppError):
    """未认证 / 登录态失效（1002）。"""

    def __init__(self, message: str = "未认证或登录态已失效", data: Any = None) -> None:
        super().__init__(1002, message, data=data)


class ForbiddenError(AppError):
    """权限不足（1003）。"""

    def __init__(self, message: str = "权限不足", data: Any = None) -> None:
        super().__init__(1003, message, data=data)


class AlreadyInitializedError(AppError):
    """系统已初始化（1004）。"""

    def __init__(self, message: str = "系统已初始化", data: Any = None) -> None:
        super().__init__(1004, message, data=data)


class NotFoundError(AppError):
    """资源不存在（2001）。"""

    def __init__(self, message: str = "资源不存在", data: Any = None) -> None:
        super().__init__(2001, message, data=data)


class StatusConflictError(AppError):
    """状态冲突（2002）。"""

    def __init__(self, message: str = "状态冲突", data: Any = None) -> None:
        super().__init__(2002, message, data=data)


class IsolationError(AppError):
    """隔离环境异常（3001）。"""

    def __init__(self, message: str = "隔离环境异常", data: Any = None) -> None:
        super().__init__(3001, message, data=data)


class InternalError(AppError):
    """内部错误（5000）。"""

    def __init__(self, message: str = "内部错误", data: Any = None) -> None:
        super().__init__(5000, message, data=data)


def ok(data: Any = None) -> dict[str, Any]:
    """构造统一成功响应体（code=0）。"""
    return {"code": 0, "message": "success", "data": data}


def fail(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """构造统一失败响应体。"""
    return {"code": code, "message": message, "data": data}
