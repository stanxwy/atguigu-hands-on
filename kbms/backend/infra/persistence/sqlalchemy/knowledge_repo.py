"""SQLAlchemy adapter for KnowledgeRepository (SPEC §9.1 SqlKnowledgeRepository)."""

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models.entities import KnowledgeUnit, UnitPermission, utcnow
from app.domain.ports.knowledge_repository import KnowledgeRepository


class SqlKnowledgeRepository(KnowledgeRepository):
    """SQLAlchemy implementation of the knowledge unit & data-permission repository."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def create_unit(self, unit: KnowledgeUnit) -> KnowledgeUnit:
        with self._session_factory() as session:
            session.add(unit)
            session.commit()
            return unit

    def update_unit(
        self,
        unit_id: str,
        *,
        title: str | None = None,
        content: str | None = None,
        summary: str | None = None,
        category: str | None = None,
        status: str | None = None,
        file_type: str | None = None,
        file_size: int | None = None,
        source_file_name: str | None = None,
    ) -> KnowledgeUnit | None:
        with self._session_factory() as session:
            unit = session.get(KnowledgeUnit, unit_id)
            if unit is None:
                return None

            if title is not None:
                unit.title = title
            if content is not None:
                unit.content = content
            if summary is not None:
                unit.summary = summary
            if category is not None:
                unit.category = category
            if status is not None:
                unit.status = status
            if file_type is not None:
                unit.file_type = file_type
            if file_size is not None:
                unit.file_size = file_size
            if source_file_name is not None:
                unit.source_file_name = source_file_name

            session.commit()
            return unit

    def soft_delete_units(self, unit_ids: list[str]) -> int:
        if not unit_ids:
            return 0
        with self._session_factory() as session:
            result = session.execute(
                update(KnowledgeUnit)
                .where(KnowledgeUnit.id.in_(unit_ids))
                .values(status="offline", updated_at=utcnow())
            )
            session.commit()
            return result.rowcount or 0

    def list_units(
        self,
        *,
        title: str | None = None,
        category: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[KnowledgeUnit], int]:
        page = max(1, page)
        page_size = max(1, page_size)
        with self._session_factory() as session:
            conditions = []
            if title:
                conditions.append(KnowledgeUnit.title.ilike(f"%{title}%"))
            if category:
                conditions.append(KnowledgeUnit.category == category)
            if status:
                conditions.append(KnowledgeUnit.status == status)

            base = select(KnowledgeUnit)
            if conditions:
                base = base.where(*conditions)

            total = session.scalar(
                select(func.count()).select_from(base.subquery())
            ) or 0

            items = list(
                session.scalars(
                    base.order_by(KnowledgeUnit.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            return items, total

    def get_unit(self, unit_id: str) -> KnowledgeUnit | None:
        with self._session_factory() as session:
            return session.get(KnowledgeUnit, unit_id)

    def replace_unit_permissions(
        self, unit_id: str, permissions: list[tuple[str, str | None]]
    ) -> None:
        with self._session_factory() as session:
            session.execute(
                delete(UnitPermission).where(UnitPermission.unit_id == unit_id)
            )
            for target_type, target_id in permissions:
                session.add(
                    UnitPermission(
                        unit_id=unit_id, target_type=target_type, target_id=target_id
                    )
                )
            session.commit()

    def get_unit_permissions(self, unit_id: str) -> list[UnitPermission]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(UnitPermission).where(UnitPermission.unit_id == unit_id)
                )
            )
