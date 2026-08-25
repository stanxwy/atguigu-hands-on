"""项目表模型（对应 SPEC §2.2.2）。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigIntPK


class Project(Base):
    """项目表：一次安全评估任务的主体。

    外键策略：``created_by`` → ``users.id`` 采用 ``ON DELETE SET NULL``。
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_path: Mapped[str] = mapped_column(String(512), nullable=False)
    task_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="created", index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
