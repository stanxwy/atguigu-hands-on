"""日志脱敏工具（对齐《安全规范》§4.4）。

统一脱敏入口 ``mask()``：对 token、密码、密钥等敏感信息替换为 ``***``，
确保任何写入日志/文件的内容不泄露明文。
"""

import re

# 敏感信息匹配模式（替换为 ***）
_SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"), "Bearer ***"),
    (re.compile(r"(password[\"']?\s*[:=]\s*)[^\s,}]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(secret[\"']?\s*[:=]\s*)[^\s,}]+", re.IGNORECASE), r"\1***"),
    (re.compile(r"(api_key[\"']?\s*[:=]\s*)[^\s,}]+", re.IGNORECASE), r"\1***"),
)


def mask(message: str) -> str:
    """对消息中的敏感信息做脱敏替换。

    Args:
        message: 原始消息字符串。

    Returns:
        脱敏后的字符串。
    """
    for pattern, replacement in _SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message
