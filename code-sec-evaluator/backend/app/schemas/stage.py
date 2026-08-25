"""阶段状态响应模型（对齐 openapi.yaml StageOut / StageListData）。"""

from datetime import datetime

from app.schemas import StrictModel


class StageOut(StrictModel):
    """阶段状态项。"""

    stage_name: str
    stage_status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None


class StageListData(StrictModel):
    """阶段列表数据。"""

    list: list[StageOut]
