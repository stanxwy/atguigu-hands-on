"""资源消耗响应模型（对齐 openapi.yaml ResourceUsageOut）。"""

from datetime import datetime

from app.schemas import StrictModel


class ResourceUsageOut(StrictModel):
    """资源消耗项。"""

    cpu_usage: float | None = None
    memory_usage: float | None = None
    token_count: int | None = None
    recorded_at: datetime


class ResourceListData(StrictModel):
    """资源消耗列表数据。"""

    list: list[ResourceUsageOut]
