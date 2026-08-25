"""角色执行状态响应模型（对齐 openapi.yaml WorkerTaskOut）。"""

from datetime import datetime

from app.schemas import StrictModel


class WorkerTaskOut(StrictModel):
    """角色任务状态项。"""

    id: int
    worker_role: str
    task_status: str
    stage_name: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WorkerListData(StrictModel):
    """角色任务列表数据。"""

    list: list[WorkerTaskOut]
