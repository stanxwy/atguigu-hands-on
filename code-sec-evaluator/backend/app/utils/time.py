"""时间序列化工具：数据库无时区 datetime 按 UTC 处理。"""

from datetime import UTC, date, datetime
from typing import Any


def ensure_utc(value: datetime) -> datetime:
    """补齐或转换为 UTC datetime，避免前端把 UTC 当成本地时间。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def serialize_datetime(value: datetime) -> str:
    """输出带时区的 ISO 8601 字符串。"""
    return ensure_utc(value).isoformat()


def normalize_datetime_response(value: Any) -> Any:
    """递归规范化响应中的日期时间，供普通 dict/list API 响应使用。"""
    if isinstance(value, datetime):
        return serialize_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: normalize_datetime_response(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_datetime_response(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_datetime_response(item) for item in value)
    return value
