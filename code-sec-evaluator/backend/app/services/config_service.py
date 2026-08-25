"""系统配置读写服务（system_config）。

对齐 SPEC §2.5：初始 6 个配置键，支持嵌套分组（isolation/task/retention）的
读取与更新，并按 ``config_type`` 做类型转换。
"""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import ParamError
from app.models.system_config import SystemConfig

# 配置键定义：key -> (config_type, default_value, description)
CONFIG_DEFS: dict[str, tuple[str, str, str]] = {
    "isolation.default_image": (
        "string",
        settings.isolation_default_image,
        "隔离环境默认镜像",
    ),
    "isolation.mount_readonly": (
        "bool",
        "true" if settings.isolation_mount_readonly else "false",
        "源码是否只读挂载",
    ),
    "isolation.network_mode": (
        "string",
        settings.isolation_network_mode,
        "容器网络模式",
    ),
    "task.default_timeout_seconds": (
        "int",
        str(settings.task_default_timeout_seconds),
        "阶段默认超时（秒）",
    ),
    "task.max_concurrency": (
        "int",
        str(settings.task_max_concurrency),
        "最大并行评估项目数",
    ),
    "retention.days": (
        "int",
        str(settings.retention_days),
        "已完成项目文件保留天数",
    ),
}

_VALID_KEYS: frozenset[str] = frozenset(CONFIG_DEFS.keys())


def cast_value(value: str, config_type: str) -> Any:
    """按配置类型将字符串值转换为对应 Python 类型。

    Args:
        value: 字符串形式的配置值。
        config_type: string/int/float/bool/json。

    Returns:
        转换后的值。

    Raises:
        ValueError: 转换失败。
    """
    if config_type == "int":
        return int(value)
    if config_type == "float":
        return float(value)
    if config_type == "bool":
        return value.strip().lower() in ("true", "1", "yes", "on")
    if config_type == "json":
        return json.loads(value)
    return value


def to_string(value: Any, config_type: str) -> str:
    """将 Python 值转换为存储字符串（cast_value 的逆操作）。"""
    if config_type == "bool":
        return "true" if bool(value) else "false"
    if config_type == "json":
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _nest(typed_map: dict[str, Any]) -> dict[str, Any]:
    """将 ``a.b.c`` 形式的扁平键映射为嵌套字典。"""
    result: dict[str, Any] = {}
    for key, value in typed_map.items():
        parts = key.split(".")
        node = result
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value
    return result


async def seed_configs(db: AsyncSession) -> None:
    """写入缺失的配置键（幂等）。"""
    existing_keys = set(
        (await db.execute(select(SystemConfig.config_key))).scalars().all()
    )
    for key, (config_type, default, description) in CONFIG_DEFS.items():
        if key not in existing_keys:
            db.add(
                SystemConfig(
                    config_key=key,
                    config_value=default,
                    config_type=config_type,
                    description=description,
                )
            )


async def get_rows(db: AsyncSession) -> dict[str, SystemConfig]:
    """返回全部配置行（key -> SystemConfig）。"""
    rows = (await db.execute(select(SystemConfig))).scalars().all()
    return {row.config_key: row for row in rows}


async def get_typed_map(db: AsyncSession) -> dict[str, Any]:
    """返回全部配置的类型化键值映射。"""
    rows = await get_rows(db)
    return {
        key: cast_value(row.config_value, row.config_type)
        for key, row in rows.items()
    }


async def get_nested(db: AsyncSession) -> dict[str, Any]:
    """返回嵌套分组的配置（isolation/task/retention）。"""
    return _nest(await get_typed_map(db))


async def get_value(db: AsyncSession, key: str, default: Any = None) -> Any:
    """读取单个配置键的类型化值。

    Args:
        db: 数据库会话。
        key: 配置键（须在 CONFIG_DEFS 内）。
        default: 键不存在或未定义时的默认值。

    Returns:
        类型化后的配置值。
    """
    row = await db.scalar(
        select(SystemConfig).where(SystemConfig.config_key == key)
    )
    if row is None:
        return default
    return cast_value(row.config_value, row.config_type)


async def update_configs(
    db: AsyncSession, updates: dict[str, Any]
) -> dict[str, Any]:
    """批量更新配置，返回仅包含被更新分组的嵌套片段。

    Args:
        db: 数据库会话。
        updates: 键值对（键须在 CONFIG_DEFS 内）。

    Returns:
        更新后的配置分组片段（如 ``{"task": {...}}``）。

    Raises:
        ParamError: 配置为空、含未知键或值类型非法。
    """
    if not updates:
        raise ParamError("config 不能为空")
    rows = await get_rows(db)
    changed_groups: set[str] = set()
    for key, raw_value in updates.items():
        if key not in _VALID_KEYS:
            raise ParamError(f"未知配置键: {key}")
        row = rows.get(key)
        if row is None:
            raise ParamError(f"配置键尚未初始化: {key}")
        try:
            typed = cast_value(str(raw_value), row.config_type)
        except (ValueError, TypeError) as exc:
            raise ParamError(f"配置值非法: {key}") from exc
        row.config_value = to_string(typed, row.config_type)
        changed_groups.add(key.split(".")[0])
    await db.commit()
    nested = await get_nested(db)
    return {group: nested[group] for group in changed_groups if group in nested}
