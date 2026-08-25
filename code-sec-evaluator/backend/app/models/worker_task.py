"""角色任务表模型（对应 SPEC §2.2.4）。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigIntPK


class WorkerTask(Base):
    """角色任务表：记录每个角色在某个阶段内的执行任务，可回溯 project/stage。"""

    __tablename__ = "worker_tasks"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_id: Mapped[int] = mapped_column(
        ForeignKey("runtime_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    worker_role: Mapped[str] = mapped_column(String(32), nullable=False)
    task_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_status: Mapped[str] = mapped_column(String(16), nullable=False, default="idle")
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
