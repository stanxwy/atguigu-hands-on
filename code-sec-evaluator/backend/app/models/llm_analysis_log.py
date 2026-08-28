"""LLM 调用分析日志表模型（可选 P1：留存 LLM 原始判定、可回溯、可审计）。

对齐《LLM集成实施文档》§9：记录每次 confirm/verify/attack_path/summary
调用的模型、任务类型、原始请求/响应、token 用量与是否降级。
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigIntPK


class LLMAnalysisLog(Base):
    """LLM 调用日志：一次 LLM 请求对应一行，承载判定/验证/编排/摘要原始记录。"""

    __tablename__ = "llm_analysis_logs"
    __table_args__ = (
        Index("ix_llm_log_project_created", "project_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("runtime_stages.id", ondelete="SET NULL"), nullable=True
    )
    vuln_id: Mapped[int | None] = mapped_column(
        ForeignKey("vulnerabilities.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # confirm / verify / attack_path / summary
    raw_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )