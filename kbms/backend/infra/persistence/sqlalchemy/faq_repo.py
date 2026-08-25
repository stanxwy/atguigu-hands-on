"""SQLAlchemy adapter for FaqRepository (SPEC §9.1 SqlFaqRepository)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models.entities import Faq, utcnow
from app.domain.ports.faq_repository import FaqRepository


class SqlFaqRepository(FaqRepository):
    """SQLAlchemy implementation of the FAQ repository."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def list_faqs(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Faq], int]:
        page = max(1, page)
        page_size = max(1, page_size)
        with self._session_factory() as session:
            conditions = []
            if status:
                conditions.append(Faq.status == status)
            if category:
                conditions.append(Faq.category == category)

            base = select(Faq)
            if conditions:
                base = base.where(*conditions)

            total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
            items = list(
                session.scalars(
                    base.order_by(Faq.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            return items, total

    def create_faq(
        self,
        *,
        question: str,
        answer: str,
        category: str | None = None,
        related_unit_id: str | None = None,
        source_type: str = "manual",
    ) -> Faq:
        faq = Faq(
            question=question,
            answer=answer,
            category=category,
            related_unit_id=related_unit_id,
            source_type=source_type,
        )
        with self._session_factory() as session:
            session.add(faq)
            session.commit()
            return faq

    def review_faq(
        self,
        faq_id: str,
        *,
        action: str,
        reviewer_id: str,
        edited_answer: str | None = None,
    ) -> Faq | None:
        with self._session_factory() as session:
            faq = session.get(Faq, faq_id)
            if faq is None:
                return None

            if action == "approve":
                faq.status = "published"
            elif action == "reject":
                faq.status = "rejected"
            else:
                return faq

            if edited_answer is not None and action == "approve":
                faq.answer = edited_answer

            faq.reviewer_id = reviewer_id
            faq.reviewed_at = utcnow()
            session.commit()
            return faq

    def get_published_faqs(self) -> list[Faq]:
        with self._session_factory() as session:
            return list(session.scalars(select(Faq).where(Faq.status == "published")))
