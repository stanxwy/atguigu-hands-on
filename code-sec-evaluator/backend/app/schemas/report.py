"""报告响应模型（对齐 openapi.yaml ReportOut）。"""

from datetime import datetime

from app.schemas import StrictModel


class ReportOut(StrictModel):
    """报告响应体。"""

    report_id: int
    report_markdown: str | None = None
    report_html: str | None = None
    created_at: datetime
