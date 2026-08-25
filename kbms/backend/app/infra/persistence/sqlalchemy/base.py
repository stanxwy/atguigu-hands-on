"""Engine / Session / DeclarativeBase assembly for the SQLAlchemy persistence layer.

This module is the single place where a database ``Engine`` and
``sessionmaker`` are built from ``Settings.DATABASE_URL``. It is
dialect-agnostic: PostgreSQL (psycopg) and SQLite (dev/test) both work via the
same code path (SQLite only adds ``check_same_thread=False``).
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models.entities import Base
from app.infra.config.settings import Settings

__all__ = ["Base", "create_engine_from_settings", "create_session_factory", "SessionFactory"]

#: Callable type that produces a new ``Session``.
SessionFactory = sessionmaker[Session]


def create_engine_from_settings(settings: Settings) -> Engine:
    """Build a SQLAlchemy ``Engine`` from settings.

    Args:
        settings: Application settings (reads ``DATABASE_URL``).

    Returns:
        A configured ``Engine``. SQLite URLs receive ``check_same_thread=False``
        so the engine can be shared across threads (FastAPI).
    """
    connect_args: dict = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


def create_session_factory(engine: Engine) -> SessionFactory:
    """Build a ``sessionmaker`` bound to ``engine``.

    ``expire_on_commit=False`` keeps committed ORM instances usable (their
    loaded column attributes remain accessible) after the repository returns
    them to the service layer.

    Args:
        engine: The SQLAlchemy engine.

    Returns:
        A ``sessionmaker`` producing ``Session`` instances.
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
