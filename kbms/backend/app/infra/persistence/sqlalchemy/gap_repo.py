"""SQLAlchemy adapter for GapRepository (SPEC §9.1 SqlGapRepository)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models.entities import KnowledgeGap
from app.domain.ports.gap_repository import GapRepository


class SqlGapRepository(GapRepository):
    """SQLAlchemy implementation of the knowledge-gap repository."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def upsert_gap(
        self,
        *,
        question_pattern: str,
        sample_questions: list[str] | None = None,
        ask_count: int = 1,
        last_asked_at: datetime | None = None,
        status: str = "unresolved",
        resolved_unit_id: str | None = None,
    ) -> KnowledgeGap:
        with self._session_factory() as session:
            gap = session.scalar(
                select(KnowledgeGap).where(
                    KnowledgeGap.question_pattern == question_pattern
                )
            )
            if gap is None:
                gap = KnowledgeGap(
                    question_pattern=question_pattern,
                    sample_questions_json=sample_questions,
                    ask_count=max(1, ask_count),
                    last_asked_at=last_asked_at,
                    status=status,
                    resolved_unit_id=resolved_unit_id,
                )
                session.add(gap)
            else:
                gap.ask_count += max(1, ask_count)
                if last_asked_at is not None:
                    gap.last_asked_at = last_asked_at
                if sample_questions:
                    gap.sample_questions_json = sample_questions
                if status != "unresolved":
                    gap.status = status
                if resolved_unit_id is not None:
                    gap.resolved_unit_id = resolved_unit_id

            session.commit()
            return gap

    def list_gaps(
        self, *, status: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[KnowledgeGap], int]:
        page = max(1, page)
        page_size = max(1, page_size)
        with self._session_factory() as session:
            base = select(KnowledgeGap)
            if status:
                base = base.where(KnowledgeGap.status == status)

            total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
            items = list(
                session.scalars(
                    base.order_by(KnowledgeGap.ask_count.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            return items, total
