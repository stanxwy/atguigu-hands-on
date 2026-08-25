"""攻击路径保存与查询服务。"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.attack_path import AttackPath, AttackPathItem
from app.utils.code_gen import next_path_code


async def create_attack_path(
    db: AsyncSession,
    project_id: int,
    *,
    path_title: str,
    path_summary: str | None = None,
    final_impact_text: str | None = None,
    items: list[tuple[int, str]] | None = None,
) -> AttackPath:
    """创建攻击路径并关联漏洞明细。

    Args:
        db: 数据库会话。
        project_id: 项目 ID。
        path_title: 路径标题。
        path_summary: 路径摘要。
        final_impact_text: 最终影响。
        items: 明细列表，每项为 ``(vuln_id, step_text)``，按给定顺序编号。

    Returns:
        新建的 AttackPath 实例（含已 flush 的明细）。
    """
    code = await next_path_code(db, project_id)
    path = AttackPath(
        project_id=project_id,
        path_code=code,
        path_title=path_title,
        path_summary=path_summary,
        final_impact_text=final_impact_text,
    )
    db.add(path)
    await db.flush()
    for order, (vuln_id, step_text) in enumerate(items or [], start=1):
        db.add(
            AttackPathItem(
                path_id=path.id,
                vuln_id=vuln_id,
                step_order=order,
                step_text=step_text,
            )
        )
    await db.flush()
    return path


async def count_attack_paths(db: AsyncSession, project_id: int) -> int:
    """统计项目攻击路径数量。"""
    return int(
        (
            await db.scalar(
                select(func.count()).where(AttackPath.project_id == project_id)
            )
        )
        or 0
    )


async def list_attack_paths(
    db: AsyncSession, project_id: int
) -> tuple[int, list[dict[str, Any]]]:
    """查询攻击路径列表（含关联漏洞数量）。"""
    rows = (
        (
            await db.execute(
                select(AttackPath)
                .where(AttackPath.project_id == project_id)
                .options(selectinload(AttackPath.items))
                .order_by(AttackPath.id)
            )
        )
        .scalars()
        .all()
    )
    total = len(rows)
    items = [
        {
            "id": path.id,
            "path_code": path.path_code,
            "path_title": path.path_title,
            "path_summary": path.path_summary,
            "final_impact_text": path.final_impact_text,
            "vuln_count": len(path.items),
            "created_at": path.created_at,
        }
        for path in rows
    ]
    return total, items


async def get_attack_path(
    db: AsyncSession, project_id: int, path_id: int
) -> dict[str, Any]:
    """查询攻击路径详情（含按顺序的明细与关联漏洞信息）。"""
    path = await db.scalar(
        select(AttackPath)
        .where(AttackPath.id == path_id, AttackPath.project_id == project_id)
        .options(selectinload(AttackPath.items).selectinload(AttackPathItem.vulnerability))
    )
    if path is None:
        raise NotFoundError("攻击路径不存在")
    items = [
        {
            "step_order": item.step_order,
            "step_text": item.step_text,
            "vuln_id": item.vuln_id,
            "vuln_code": item.vulnerability.vuln_code if item.vulnerability else None,
            "vuln_title": item.vulnerability.vuln_title if item.vulnerability else None,
        }
        for item in path.items
    ]
    return {
        "id": path.id,
        "path_code": path.path_code,
        "path_title": path.path_title,
        "path_summary": path.path_summary,
        "final_impact_text": path.final_impact_text,
        "items": items,
    }
