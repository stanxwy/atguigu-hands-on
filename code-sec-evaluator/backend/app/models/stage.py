"""执行阶段表模型（对应 SPEC §2.2.3）。"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigIntPK


class RuntimeStage(Base):
    """执行阶段表：每个项目每个阶段一条记录。

    约束：``UNIQUE(project_id, stage_name)``。
    """

    __tablename__ = "runtime_stages"
    __table_args__ = (
        UniqueConstraint("project_id", "stage_name", name="uq_stage_project_name"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage_name: Mapped[str] = mapped_column(String(32), nullable=False)
    stage_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
