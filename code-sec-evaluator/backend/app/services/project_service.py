"""项目服务：CRUD、列表/详情、阶段/角色查询、级联删除（SPEC §2.4）。"""

import asyncio
import logging
import shutil
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import NotFoundError
from app.models.project import Project
from app.models.report import Report
from app.models.stage import RuntimeStage
from app.models.user import User
from app.models.worker_task import WorkerTask
from app.schemas.project import ProjectCreate
from app.services import attack_path_service, vulnerability_service
from app.services.isolation_service import isolation_service
from app.utils.path_safety import validate_host_path

logger = logging.getLogger("app.project")


async def create_project(
    db: AsyncSession, user: User, data: ProjectCreate
) -> Project:
    """创建项目（初始状态 created）。

    对 ``local_path`` 做语义校验（绝对 + 存在）。
    """
    if data.source_type == "local_path":
        validate_host_path(data.source_path)
    project = Project(
        project_name=data.project_name,
        source_type=data.source_type,
        source_path=data.source_path,
        task_content=data.task_content,
        project_status="created",
        created_by=user.id,
    )
    db.add(project)
    await db.flush()
    return project


async def _stage_timing(
    db: AsyncSession, project_ids: list[int]
) -> dict[int, tuple[Any, Any]]:
    """聚合每个项目的阶段最早开始/最晚结束时间。"""
    if not project_ids:
        return {}
    rows = (
        await db.execute(
            select(
                RuntimeStage.project_id,
                func.min(RuntimeStage.started_at),
                func.max(RuntimeStage.finished_at),
            )
            .where(RuntimeStage.project_id.in_(project_ids))
            .group_by(RuntimeStage.project_id)
        )
    ).all()
    return {pid: (min_started, max_finished) for pid, min_started, max_finished in rows}


async def list_projects(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    page_size: int = 10,
    project_status: str | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """分页查询项目列表（普通用户仅见自己 created_by 的项目，防 IDOR）。"""
    count_stmt = select(func.count()).select_from(Project)
    stmt = select(Project)
    if user.role != "admin":
        count_stmt = count_stmt.where(Project.created_by == user.id)
        stmt = stmt.where(Project.created_by == user.id)
    if project_status:
        count_stmt = count_stmt.where(Project.project_status == project_status)
        stmt = stmt.where(Project.project_status == project_status)
    total = int((await db.scalar(count_stmt)) or 0)
    rows = (
        (
            await db.execute(
                stmt.order_by(Project.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    timing = await _stage_timing(db, [p.id for p in rows])
    items = [
        {
            "id": p.id,
            "project_name": p.project_name,
            "source_type": p.source_type,
            "project_status": p.project_status,
            "last_started_at": timing.get(p.id, (None, None))[0],
            "last_finished_at": timing.get(p.id, (None, None))[1],
        }
        for p in rows
    ]
    return total, items


async def get_project_detail(db: AsyncSession, project: Project) -> dict[str, Any]:
    """组装项目详情（含漏洞/路径计数与报告状态）。"""
    vuln_count = await vulnerability_service.count_vulnerabilities(db, project.id)
    attack_path_count = await attack_path_service.count_attack_paths(db, project.id)
    report = await db.scalar(select(Report).where(Report.project_id == project.id))
    return {
        "id": project.id,
        "project_name": project.project_name,
        "source_type": project.source_type,
        "source_path": project.source_path,
        "task_content": project.task_content,
        "project_status": project.project_status,
        "vuln_count": vuln_count,
        "attack_path_count": attack_path_count,
        "report_status": "generated" if report is not None else "none",
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


async def get_stages(db: AsyncSession, project_id: int) -> list[dict[str, Any]]:
    """查询阶段状态列表（按创建顺序）。"""
    rows = (
        (
            await db.execute(
                select(RuntimeStage)
                .where(RuntimeStage.project_id == project_id)
                .order_by(RuntimeStage.id)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "stage_name": stage.stage_name,
            "stage_status": stage.stage_status,
            "started_at": stage.started_at,
            "finished_at": stage.finished_at,
        }
        for stage in rows
    ]


async def get_workers(db: AsyncSession, project_id: int) -> list[dict[str, Any]]:
    """查询角色执行状态列表（附阶段名）。"""
    rows = (
        await db.execute(
            select(WorkerTask, RuntimeStage.stage_name)
            .outerjoin(RuntimeStage, WorkerTask.stage_id == RuntimeStage.id)
            .where(WorkerTask.project_id == project_id)
            .order_by(WorkerTask.id)
        )
    ).all()
    return [
        {
            "id": task.id,
            "worker_role": task.worker_role,
            "task_status": task.task_status,
            "stage_name": stage_name,
            "started_at": task.started_at,
            "finished_at": task.finished_at,
        }
        for task, stage_name in rows
    ]


async def delete_project(db: AsyncSession, project: Project) -> int:
    """删除项目（SPEC §2.4 删除事务）。

    顺序：① 销毁隔离容器 → ② 级联删除业务数据 → ③ 清理文件目录
    （文件清理失败不阻塞事务，仅告警）。

    Args:
        db: 数据库会话。
        project: 已通过归属校验的项目实例。

    Returns:
        被删除的项目 ID。
    """
    project_id = project.id
    # ① 销毁容器（失败不阻塞，内部已告警）
    await isolation_service.destroy_environment(project_id)
    # ② 级联删除（ORM + 外键 ondelete=CASCADE）
    await db.delete(project)
    await db.commit()
    # ③ 文件目录清理
    await asyncio.to_thread(_cleanup_project_files, project_id)
    return project_id


def _cleanup_project_files(project_id: int) -> None:
    """清理项目相关的文件目录（日志/报告/工作区）。"""
    for root in (settings.log_path, settings.report_path, settings.workspace_path):
        target = root / str(project_id)
        if not target.exists():
            continue
        try:
            shutil.rmtree(target)
        except OSError as exc:  # noqa: BLE001  见 SPEC §2.4 文件删除失败不阻塞
            logger.warning("清理项目文件目录失败（不阻塞删除事务）: %s -> %s", target, exc)


async def require_project(db: AsyncSession, project_id: int) -> Project:
    """按 ID 获取项目，不存在则抛 NotFoundError。"""
    project = await db.get(Project, project_id)
    if project is None:
        raise NotFoundError("项目不存在")
    return project
