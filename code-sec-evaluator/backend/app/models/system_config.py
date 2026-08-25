"""系统配置表模型（对应 SPEC §2.2.12 / §2.5）。"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigIntPK


class SystemConfig(Base):
    """系统配置表：键值对存储，``config_type`` 决定值的类型转换。"""

    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    config_type: Mapped[str] = mapped_column(String(16), nullable=False, default="string")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
