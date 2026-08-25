"""调度器：阶段状态机 + 信号量控并发 + 后台任务推进。

对齐 SPEC §1.2.6（asyncio 自研调度 + ThreadPoolExecutor 跑阻塞 IO）与 §5.2 时序：
启动先准备隔离环境再推进阶段；stop 后当前阶段不再推进。
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import PROJECT_STARTABLE, STAGE_ORDER
from app.core.errors import NotFoundError, StatusConflictError
from app.database import async_session_factory
from app.models.project import Project
from app.models.stage import RuntimeStage
from app.services import config_service, worker_service
from app.services.isolation_service import isolation_service
from app.services.monitor_service import monitor_service

logger = logging.getLogger("app.scheduler")

# 阶段 → 角色派发顺序（generic 编排 + ops 巡检分别挂在首尾阶段）
STAGE_ROLES: dict[str, list[str]] = {
    "environment_scan": ["generic", "env_check"],
    "code_analysis": ["code_analyze"],
    "vulnerability_verify": ["vuln_verify"],
    "report_generate": ["report_gen", "ops"],
}

_ALL_STAGES: tuple[str, ...] = (*STAGE_ORDER, "done")


class Scheduler:
    """阶段调度器：控制项目评估流水线的并发与状态推进。"""

    def __init__(self) -> None:
        self._concurrency = settings.task_max_concurrency
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self._stop_flags: dict[int, asyncio.Event] = {}
        self._running_tasks: dict[int, asyncio.Task[None]] = {}

    async def _sync_concurrency(self, db: AsyncSession) -> None:
        """按系统配置同步最大并发数（无任务运行时替换信号量）。"""
        max_concurrency = int(
            await config_service.get_value(
                db, "task.max_concurrency", settings.task_max_concurrency
            )
        )
        if max_concurrency != self._concurrency and not self._running_tasks:
            self._concurrency = max_concurrency
            self._semaphore = asyncio.Semaphore(max_concurrency)

    async def start(self, project_id: int) -> Project:
        """启动评估任务（受理后异步执行）。

        Raises:
            NotFoundError: 项目不存在。
            StatusConflictError: 当前状态不允许启动（2002）。
        """
        async with async_session_factory() as db:
            project = await db.get(Project, project_id)
            if project is None:
                raise NotFoundError("项目不存在")
            if project.project_status not in PROJECT_STARTABLE:
                raise StatusConflictError("当前状态不允许启动")
            await self._sync_concurrency(db)
            project.project_status = "running"
            await self._reset_stages(db, project_id)
            await db.commit()
            monitor_service.publish(
                project_id, "project_status", {"project_status": "running"}
            )
            self._stop_flags[project_id] = asyncio.Event()
            task = asyncio.create_task(self._run_pipeline(project_id))
            self._running_tasks[project_id] = task
            return project

    async def stop(self, project_id: int) -> Project:
        """停止评估任务（置位停止标志，后台流水线随后退出）。

        Raises:
            NotFoundError: 项目不存在。
            StatusConflictError: 当前状态非 running（2002）。
        """
        async with async_session_factory() as db:
            project = await db.get(Project, project_id)
            if project is None:
                raise NotFoundError("项目不存在")
            if project.project_status != "running":
                raise StatusConflictError("当前状态不允许停止")
            project.project_status = "stopped"
            await db.commit()
        stop_flag = self._stop_flags.get(project_id)
        if stop_flag is not None:
            stop_flag.set()
        monitor_service.publish(
            project_id, "project_status", {"project_status": "stopped"}
        )
        return project

    async def _reset_stages(self, db: AsyncSession, project_id: int) -> None:
        """重建/重置 5 个阶段记录为 pending。"""
        existing = {
            stage.stage_name: stage
            for stage in (
                (
                    await db.execute(
                        select(RuntimeStage).where(
                            RuntimeStage.project_id == project_id
                        )
                    )
                )
                .scalars()
                .all()
            )
        }
        for name in _ALL_STAGES:
            stage = existing.get(name)
            if stage is None:
                db.add(
                    RuntimeStage(
                        project_id=project_id, stage_name=name, stage_status="pending"
                    )
                )
            else:
                stage.stage_status = "pending"
                stage.started_at = None
                stage.finished_at = None
                stage.error_message = None

    async def _run_pipeline(self, project_id: int) -> None:
        """后台流水线：受信号量控制，异常兜底置 failed。"""
        async with self._semaphore:
            async with async_session_factory() as db:
                try:
                    await self._execute_pipeline(db, project_id)
                except Exception:  # noqa: BLE001  后台任务须兜底
                    logger.exception("项目 %s 流水线异常", project_id)
                    await self._finalize(db, project_id, "failed")
                finally:
                    self._running_tasks.pop(project_id, None)
                    self._stop_flags.pop(project_id, None)

    async def _execute_pipeline(
        self, db: AsyncSession, project_id: int
    ) -> None:
        """推进阶段状态机。"""
        stop_flag = self._stop_flags.get(project_id)
        project = await db.get(Project, project_id)
        if project is None:
            return

        await monitor_service.append_log(
            db, project_id, "info", "开始准备隔离环境"
        )
        source_dir = await isolation_service.resolve_source_dir(project)
        await isolation_service.prepare_environment(db, project, source_dir)
        await db.commit()

        for stage_name in STAGE_ORDER:
            if stop_flag is not None and stop_flag.is_set():
                await isolation_service.destroy_environment(project_id)
                await self._finalize(db, project_id, "stopped")
                return

            stage = await self._get_stage(db, project_id, stage_name)
            if stage is None:
                continue
            stage.stage_status = "running"
            stage.started_at = datetime.now(UTC)
            await db.commit()
            monitor_service.publish(
                project_id,
                "stage_status",
                {"stage_name": stage_name, "stage_status": "running"},
            )

            stage_ok = True
            for role in STAGE_ROLES.get(stage_name, []):
                role_ok = await self._dispatch_role(db, project, stage, role, source_dir)
                if not role_ok:
                    stage_ok = False
                    break

            if not stage_ok:
                stage.stage_status = "failed"
                stage.finished_at = datetime.now(UTC)
                stage.error_message = f"阶段 {stage_name} 角色执行失败"
                await db.commit()
                monitor_service.publish(
                    project_id,
                    "stage_status",
                    {"stage_name": stage_name, "stage_status": "failed"},
                )
                await isolation_service.destroy_environment(project_id)
                await self._finalize(db, project_id, "failed")
                return

            stage.stage_status = "success"
            stage.finished_at = datetime.now(UTC)
            await db.commit()
            monitor_service.publish(
                project_id,
                "stage_status",
                {"stage_name": stage_name, "stage_status": "success"},
            )

        # 终态 done 阶段
        done_stage = await self._get_stage(db, project_id, "done")
        if done_stage is not None:
            now = datetime.now(UTC)
            done_stage.stage_status = "success"
            done_stage.started_at = done_stage.started_at or now
            done_stage.finished_at = now
        await db.commit()

        await isolation_service.destroy_environment(project_id)
        await self._finalize(db, project_id, "completed")

    async def _dispatch_role(
        self,
        db: AsyncSession,
        project: Project,
        stage: RuntimeStage,
        role: str,
        source_dir: Any,
    ) -> bool:
        """按角色派发 worker_service 任务。"""
        if role == "generic":
            return await worker_service.run_generic(db, project, stage.id)
        if role == "env_check":
            return await worker_service.run_env_check(db, project, stage.id, source_dir)
        if role == "code_analyze":
            return await worker_service.run_code_analyze(
                db, project, stage.id, source_dir
            )
        if role == "vuln_verify":
            return await worker_service.run_vuln_verify(db, project, stage.id)
        if role == "report_gen":
            return await worker_service.run_report_gen(db, project, stage.id)
        if role == "ops":
            return await worker_service.run_ops(db, project, stage.id)
        return False

    async def _finalize(self, db: AsyncSession, project_id: int, status: str) -> None:
        """设置项目终态并推送事件。"""
        project = await db.get(Project, project_id)
        if project is not None:
            project.project_status = status
        await db.commit()
        monitor_service.publish(
            project_id, "project_status", {"project_status": status}
        )

    @staticmethod
    async def _get_stage(
        db: AsyncSession, project_id: int, stage_name: str
    ) -> RuntimeStage | None:
        """按项目+阶段名获取阶段记录。"""
        return await db.scalar(
            select(RuntimeStage).where(
                RuntimeStage.project_id == project_id,
                RuntimeStage.stage_name == stage_name,
            )
        )


scheduler = Scheduler()
