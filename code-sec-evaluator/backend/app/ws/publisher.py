"""内存 Pub/Sub 事件总线（按 project_id 分组广播，单实例足够）。

多实例扩展时可替换为 Redis Pub/Sub，接口保持不变（SPEC §1.2.7）。
"""

import asyncio
from typing import Any


class EventPublisher:
    """按 project_id 维护订阅者队列，向项目内所有订阅者广播事件。"""

    def __init__(self) -> None:
        self._subscribers: dict[int, set[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, project_id: int, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """注册一个项目订阅队列。"""
        self._subscribers.setdefault(project_id, set()).add(queue)

    def unsubscribe(
        self, project_id: int, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        """移除一个项目订阅队列。"""
        subscribers = self._subscribers.get(project_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(project_id, None)

    def publish(self, project_id: int, message: dict[str, Any]) -> None:
        """向项目所有订阅队列广播消息（非阻塞，队列满则丢弃）。"""
        for queue in list(self._subscribers.get(project_id, ())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # 消费端过慢时丢弃，避免内存膨胀（监控场景可接受）
                continue


publisher = EventPublisher()
