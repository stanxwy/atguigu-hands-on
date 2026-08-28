"""数据库基础设施：异步引擎、会话工厂与声明式 Base。

对齐《SPEC》§1.1 选型（SQLAlchemy 2.0 异步）与《编码规范》§5.2
（统一继承 ``Base``，模型用 ``Mapped``/``mapped_column``）。
"""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import BigInteger, Integer, event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


# 主键类型：MySQL 用 BIGINT（对齐 SPEC §2.1 主键约定），SQLite 用 INTEGER。
# SQLite 仅 ``INTEGER PRIMARY KEY`` 自动生成 rowid（BIGINT 不会），故需 variant。
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


def _ensure_sqlite_dir() -> None:
    """确保 SQLite 数据库文件父目录存在（否则 aiosqlite 无法建库）。"""
    if not settings.database_url.startswith("sqlite"):
        return
    url = make_url(settings.database_url)
    if url.database and url.database != ":memory:":
        db_path = Path(url.database)
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir()


engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)


if engine.dialect.name == "sqlite":
    # SQLite 默认关闭外需约束，需显式开启以支持 ON DELETE CASCADE（SPEC §2.4）
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：提供请求级异步数据库会话。"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_models() -> None:
    """建表（幂等）。导入全部模型以注册到 ``Base.metadata`` 后执行 create_all。"""
    import app.models  # noqa: F401  确保模型已注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
