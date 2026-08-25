"""WebSocket 连接管理器（按 project_id 管理订阅连接）。"""

import asyncio
from typing import Any

from fastapi import WebSocket

from app.ws.publisher import publisher


class WebSocketManager:
    """维护每个项目的连接集合与广播任务。

    每个项目对应一个 ``asyncio.Queue``（已订阅到 EventPublisher），由独立的
    后台任务从队列取事件并发送给该项目所有连接；连接断开即移除。
    """

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}
        self._queues: dict[int, asyncio.Queue[dict[str, Any]]] = {}
        self._tasks: dict[int, asyncio.Task[None]] = {}

    async def connect(self, project_id: int, websocket: WebSocket) -> None:
        """建立连接并启动该项目的广播任务（幂等）。"""
        if project_id not in self._connections:
            self._connections[project_id] = set()
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
            self._queues[project_id] = queue
            publisher.subscribe(project_id, queue)
            self._tasks[project_id] = asyncio.create_task(self._broadcast(project_id))
        self._connections[project_id].add(websocket)

    async def disconnect(self, project_id: int, websocket: WebSocket) -> None:
        """移除连接；当项目无连接时清理队列与广播任务。"""
        connections = self._connections.get(project_id)
        if connections is not None:
            connections.discard(websocket)
            if connections:
                return
        await self._cleanup(project_id)

    async def _cleanup(self, project_id: int) -> None:
        """回收项目相关的队列、订阅与后台任务。"""
        self._connections.pop(project_id, None)
        queue = self._queues.pop(project_id, None)
        if queue is not None:
            publisher.unsubscribe(project_id, queue)
        task = self._tasks.pop(project_id, None)
        if task is not None:
            task.cancel()

    async def _broadcast(self, project_id: int) -> None:
        """从项目队列取事件并广播给所有连接。"""
        queue = self._queues[project_id]
        while True:
            message = await queue.get()
            for websocket in list(self._connections.get(project_id, set())):
                try:
                    await websocket.send_json(message)
                except Exception:
                    await self.disconnect(project_id, websocket)


manager = WebSocketManager()
