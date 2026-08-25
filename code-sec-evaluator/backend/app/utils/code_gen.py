"""编号生成工具（VULN-XXXX / PATH-XXXX）。

编号在项目内自增（``VULN-0001``、``VULN-0002``…），跨项目独立；
生成时以「当前项目最大序号 + 1」为准，保证唯一且可回溯。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attack_path import AttackPath
from app.models.vulnerability import Vulnerability

_PREFIX_WIDTH = 4


async def next_vuln_code(db: AsyncSession, project_id: int) -> str:
    """为指定项目生成下一个漏洞编号（如 VULN-0001）。"""
    max_code = await db.scalar(
        select(func.max(Vulnerability.vuln_code)).where(
            Vulnerability.project_id == project_id
        )
    )
    return _next_code("VULN", max_code)


async def next_path_code(db: AsyncSession, project_id: int) -> str:
    """为指定项目生成下一个攻击路径编号（如 PATH-0001）。"""
    max_code = await db.scalar(
        select(func.max(AttackPath.path_code)).where(AttackPath.project_id == project_id)
    )
    return _next_code("PATH", max_code)


def _next_code(prefix: str, max_code: str | None) -> str:
    """根据现有最大编号计算下一个编号。

    Args:
        prefix: 编号前缀（VULN / PATH）。
        max_code: 当前最大编号字符串（可为 None）。

    Returns:
        形如 ``{prefix}-0001`` 的新编号。
    """
    current_max = 0
    if max_code:
        try:
            current_max = int(max_code.split("-", 1)[1])
        except (IndexError, ValueError):
            current_max = 0
    return f"{prefix}-{current_max + 1:0{_PREFIX_WIDTH}d}"
