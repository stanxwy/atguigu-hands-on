"""运行日志表模型（对应 SPEC §2.2.9）。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigIntPK


class RuntimeLog(Base):
    """运行日志表：评估过程中的运行日志（区别于 chat_messages）。"""

    __tablename__ = "runtime_logs"
    __table_args__ = (
        Index("ix_runtime_logs_project_created", "project_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("runtime_stages.id", ondelete="SET NULL"), nullable=True
    )
    worker_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("worker_tasks.id", ondelete="SET NULL"), nullable=True
    )
    log_level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    log_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
