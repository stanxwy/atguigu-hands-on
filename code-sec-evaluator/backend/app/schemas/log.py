"""运行日志响应模型（对齐 openapi.yaml LogOut / LogListData）。"""

from datetime import datetime

from app.schemas import StrictModel


class LogOut(StrictModel):
    """运行日志项。"""

    id: int
    log_level: str
    log_content: str
    stage_name: str | None = None
    created_at: datetime


class LogListData(StrictModel):
    """运行日志列表数据。"""

    total: int
    list: list[LogOut]
