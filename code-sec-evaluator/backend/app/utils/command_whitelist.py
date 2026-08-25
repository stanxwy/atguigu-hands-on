"""命令白名单（对齐《安全规范》§2.5）。

核心原则：命令白名单 + 参数校验 + **参数数组执行**，禁止 shell 字符串拼接。
仅内置只读命令，严格禁止 sh/bash、管道、重定向、命令替换、链接符，以及任何
具备写权限或网络能力的命令（curl/wget/nc/ssh/git clone 等）。
"""

from dataclasses import dataclass

from app.core.errors import IsolationError
from app.utils.path_safety import validate_container_path


@dataclass(frozen=True)
class CommandSpec:
    """单个命令的白名单规格。

    Attributes:
        argv0: 可执行文件（容器内以 PATH 解析；宿主机回退同样适用）。
        allowed_flags: 允许的选项集合。
        allow_path_arg: 是否允许路径参数（须先经容器路径校验）。
    """

    argv0: str
    allowed_flags: frozenset[str]
    allow_path_arg: bool = True


# 只读命令白名单（SPEC §2.5.1 / 安全规范 §2.5.1）
COMMAND_WHITELIST: dict[str, CommandSpec] = {
    "grep": CommandSpec("grep", frozenset({"-r", "-n", "-i", "-E", "-l", "-c", "-I"})),
    "find": CommandSpec(
        "find", frozenset({"-type", "-name", "-maxdepth", "-print"})
    ),
    "cat": CommandSpec("cat", frozenset({"-n"})),
    "head": CommandSpec("head", frozenset({"-n"})),
    "tail": CommandSpec("tail", frozenset({"-n"})),
    "sed": CommandSpec("sed", frozenset({"-n"})),
    "ls": CommandSpec("ls", frozenset({"-l", "-a", "-R"})),
    "file": CommandSpec("file", frozenset({"b"})),
    "stat": CommandSpec("stat", frozenset()),
}


def build_command(name: str, flags: list[str], target: str) -> list[str]:
    """构建参数数组形式的安全命令。

    Args:
        name: 命令名（必须在白名单内）。
        flags: 选项列表（每个选项必须在白名单允许集合内）。
        target: 目标路径（须通过容器路径校验，防路径穿越）。

    Returns:
        参数数组（``[argv0, *flags, target]``），可直接交给 docker exec / subprocess。

    Raises:
        IsolationError: 命令不在白名单、含非法选项或目标路径非法。
    """
    spec = COMMAND_WHITELIST.get(name)
    if spec is None:
        raise IsolationError(f"命令不在白名单: {name}")
    for flag in flags:
        if flag not in spec.allowed_flags:
            raise IsolationError(f"非法选项: {name} {flag}")
    if spec.allow_path_arg:
        target = validate_container_path(target)
    return [spec.argv0, *flags, target]


def escape_literal(pattern: str) -> str:
    """将关键字转义为正则字面量，防止被当作正则元字符注入。

    关键字搜索时作为字面量匹配使用（《安全规范》§2.5.3）。

    Args:
        pattern: 原始关键字。

    Returns:
        经 ``re.escape`` 处理后的字面量模式。
    """
    import re

    return re.escape(pattern)
