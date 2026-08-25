"""攻击路径响应模型（对齐 openapi.yaml AttackPathOut / AttackPathDetailOut）。"""

from datetime import datetime

from app.schemas import StrictModel


class AttackPathOut(StrictModel):
    """攻击路径列表项。"""

    id: int
    path_code: str
    path_title: str
    path_summary: str | None = None
    final_impact_text: str | None = None
    vuln_count: int = 0
    created_at: datetime


class AttackPathItemOut(StrictModel):
    """攻击路径明细项。"""

    step_order: int
    step_text: str | None = None
    vuln_id: int
    vuln_code: str | None = None
    vuln_title: str | None = None


class AttackPathDetailOut(StrictModel):
    """攻击路径详情。"""

    id: int
    path_code: str
    path_title: str
    path_summary: str | None = None
    final_impact_text: str | None = None
    items: list[AttackPathItemOut]


class AttackPathListData(StrictModel):
    """攻击路径列表数据。"""

    total: int
    list: list[AttackPathOut]
