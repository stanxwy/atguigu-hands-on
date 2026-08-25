"""文件路径校验与防路径穿越（对齐《安全规范》§2.6）。

规则：
- ``local_path`` 必须绝对路径，拒绝相对路径；
- 规范化（realpath 解析符号链接）后校验存在性；
- 容器内路径仅允许 ``/src`` 只读挂载点下，且不得含 ``..`` 穿越。
"""

import os
from pathlib import Path

from app.core.errors import IsolationError, ParamError


def validate_host_path(path: str) -> Path:
    """校验宿主机源码路径（绝对 + 存在 + 解析符号链接）。

    说明：P0 场景下 ``source_path`` 由授权用户自行提供（指向其被评估目标），
    隔离边界由容器的只读挂载 + ``network=none`` 兜底；本函数保证路径
    「绝对 + 存在 + 无控制字符」，不做 workspace 强制圈定（见回传说明）。

    Args:
        path: 用户提供的本地绝对路径。

    Returns:
        规范化后的绝对路径 ``Path``。

    Raises:
        ParamError: 非绝对路径、含控制字符或路径不存在。
    """
    if not os.path.isabs(path):
        raise ParamError("local_path 必须为绝对路径")
    if any(ord(ch) < 32 for ch in path):
        raise ParamError("路径含非法控制字符")
    real = Path(os.path.realpath(path))
    if not real.exists():
        raise ParamError(f"路径不存在: {path}")
    return real


def ensure_within_workspace(path: Path, root: Path) -> Path:
    """校验路径落在允许的工作区根内（生产环境的严格圈定，可选启用）。

    Args:
        path: 待校验的规范化路径。
        root: 工作区根目录。

    Returns:
        规范化后的路径。

    Raises:
        ParamError: 路径越界（不在 root 内）。
    """
    root_real = Path(os.path.realpath(root))
    path_real = Path(os.path.realpath(path))
    try:
        path_real.relative_to(root_real)
    except ValueError as exc:
        raise ParamError("路径越界: 不允许访问工作区之外的路径") from exc
    return path_real


def validate_container_path(path: str) -> str:
    """校验容器内路径（仅允许 ``/src`` 下，防穿越）。

    Args:
        path: 容器内路径。

    Returns:
        规范化后的容器内路径。

    Raises:
        IsolationError: 路径不在 ``/src`` 下或含 ``..`` 穿越。
    """
    norm = os.path.normpath(path)
    if norm != "/src" and not norm.startswith("/src/"):
        raise IsolationError("容器内路径必须位于 /src/ 下")
    if ".." in Path(norm).parts:
        raise IsolationError("检测到路径穿越")
    return norm
