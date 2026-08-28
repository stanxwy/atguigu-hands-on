"""实时监控服务：事件发布（WebSocket）+ 运行日志/聊天/资源采集（psutil）。

对齐 SPEC §1.2.7（内存 Pub/Sub）与《安全规范》§4.4（日志脱敏）。
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import psutil
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.resource_usage import ResourceUsage
from app.models.runtime_log import RuntimeLog
from app.models.stage import RuntimeStage
from app.utils.logging import mask
from app.utils.time import serialize_datetime
from app.ws.publisher import publisher


def _envelope(project_id: int, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """构造 WebSocket 统一外层结构（SPEC §2.6）。"""
    return {
        "type": event_type,
        "project_id": project_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": data,
    }


class MonitorService:
    """监控服务：统一事件出口 + 日志/聊天/资源持久化与查询。"""

    def publish(self, project_id: int, event_type: str, data: dict[str, Any]) -> None:
        """发布实时事件（不落库，仅供 WebSocket 推送）。"""
        publisher.publish(project_id, _envelope(project_id, event_type, data))

    async def append_log(
        self,
        db: AsyncSession,
        project_id: int,
        level: str,
        content: str,
        *,
        stage_id: int | None = None,
        worker_task_id: int | None = None,
    ) -> RuntimeLog:
        """持久化运行日志并推送 runtime_log 事件（内容脱敏）。"""
        content = mask(content)
        row = RuntimeLog(
            project_id=project_id,
            stage_id=stage_id,
            worker_task_id=worker_task_id,
            log_level=level,
            log_content=content,
        )
        db.add(row)
        await db.flush()
        self.publish(
            project_id,
            "runtime_log",
            {
                "log_level": level,
                "log_content": content,
                "created_at": serialize_datetime(row.created_at),
            },
        )
        return row

    async def append_chat(
        self,
        db: AsyncSession,
        project_id: int,
        worker_role: str,
        message_type: str,
        message_text: str,
    ) -> ChatMessage:
        """持久化聊天消息并推送 chat_message 事件（内容脱敏）。"""
        message_text = mask(message_text)
        row = ChatMessage(
            project_id=project_id,
            worker_role=worker_role,
            message_type=message_type,
            message_text=message_text,
        )
        db.add(row)
        await db.flush()
        self.publish(
            project_id,
            "chat_message",
            {
                "worker_role": worker_role,
                "message_type": message_type,
                "message_text": message_text,
            },
        )
        return row

    async def record_resource(
        self,
        db: AsyncSession,
        project_id: int,
        *,
        cpu_usage: float | None = None,
        memory_usage: float | None = None,
        token_count: int | None = None,
    ) -> ResourceUsage:
        """持久化资源消耗并推送 resource_usage 事件。"""
        row = ResourceUsage(
            project_id=project_id,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            token_count=token_count,
        )
        db.add(row)
        await db.flush()
        self.publish(
            project_id,
            "resource_usage",
            {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "token_count": token_count,
                "recorded_at": serialize_datetime(row.recorded_at),
            },
        )
        return row

    @staticmethod
    def _sample_host() -> tuple[float, float]:
        """采集宿主机 CPU 使用率（%）与内存使用率（%）。"""
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        return float(cpu), float(mem)

    async def collect_and_record(
        self,
        db: AsyncSession,
        project_id: int,
        token_count: int | None = None,
    ) -> ResourceUsage:
        """采集宿主机资源并落库/推送（阻塞 IO 移出事件循环）。"""
        cpu, mem = await asyncio.to_thread(self._sample_host)
        return await self.record_resource(
            db, project_id, cpu_usage=cpu, memory_usage=mem, token_count=token_count
        )

    async def list_logs(
        self,
        db: AsyncSession,
        project_id: int,
        *,
        level: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[dict[str, Any]]]:
        """分页查询运行日志（附阶段名）。"""
        count_stmt = select(func.count()).where(RuntimeLog.project_id == project_id)
        if level:
            count_stmt = count_stmt.where(RuntimeLog.log_level == level)
        total = int((await db.scalar(count_stmt)) or 0)

        stmt = (
            select(RuntimeLog, RuntimeStage.stage_name)
            .outerjoin(RuntimeStage, RuntimeLog.stage_id == RuntimeStage.id)
            .where(RuntimeLog.project_id == project_id)
        )
        if level:
            stmt = stmt.where(RuntimeLog.log_level == level)
        stmt = stmt.order_by(RuntimeLog.id.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        rows = (await db.execute(stmt)).all()
        items = [
            {
                "id": log.id,
                "log_level": log.log_level,
                "log_content": log.log_content,
                "stage_name": stage_name,
                "created_at": log.created_at,
            }
            for log, stage_name in rows
        ]
        return total, items

    async def list_resources(
        self, db: AsyncSession, project_id: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        """查询最近 N 条资源消耗（按时间升序返回）。"""
        rows = (
            (
                await db.execute(
                    select(ResourceUsage)
                    .where(ResourceUsage.project_id == project_id)
                    .order_by(ResourceUsage.id.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        items = [
            {
                "cpu_usage": row.cpu_usage,
                "memory_usage": row.memory_usage,
                "token_count": row.token_count,
                "recorded_at": row.recorded_at,
            }
            for row in reversed(rows)
        ]
        return items


monitor_service = MonitorService()
