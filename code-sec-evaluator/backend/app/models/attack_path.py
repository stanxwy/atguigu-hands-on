"""攻击路径表模型（对应 SPEC §2.2.6 / §2.2.7）。"""

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, BigIntPK
from app.models.vulnerability import Vulnerability


class AttackPath(Base):
    """攻击路径表：将若干漏洞串联为可被利用的攻击链。

    约束：``UNIQUE(project_id, path_code)``。
    """

    __tablename__ = "attack_paths"
    __table_args__ = (
        UniqueConstraint("project_id", "path_code", name="uq_path_project_code"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    path_code: Mapped[str] = mapped_column(String(64), nullable=False)
    path_title: Mapped[str] = mapped_column(String(255), nullable=False)
    path_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_impact_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    items: Mapped[list["AttackPathItem"]] = relationship(
        back_populates="path",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AttackPathItem.step_order",
    )


class AttackPathItem(Base):
    """攻击路径明细表：路径内按顺序关联的漏洞步骤。

    约束：``UNIQUE(path_id, step_order)``。
    """

    __tablename__ = "attack_path_items"
    __table_args__ = (
        UniqueConstraint("path_id", "step_order", name="uq_path_item_step"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    path_id: Mapped[int] = mapped_column(
        ForeignKey("attack_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vuln_id: Mapped[int] = mapped_column(
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    path: Mapped["AttackPath"] = relationship(back_populates="items")
    vulnerability: Mapped[Vulnerability] = relationship()
