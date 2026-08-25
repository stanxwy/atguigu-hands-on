"""Knowledge-gap repository port (SPEC §9.1 GapRepository)."""

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.models.entities import KnowledgeGap


class GapRepository(ABC):
    """Persistence port for knowledge_gaps (question gaps aggregation)."""

    @abstractmethod
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
        """Upsert a gap by ``question_pattern``.

        If an existing gap matches ``question_pattern``, its ``ask_count`` is
        incremented by ``ask_count`` and ``last_asked_at``/``status`` updated;
        otherwise a new gap is created.
        """

    @abstractmethod
    def list_gaps(
        self, *, status: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[KnowledgeGap], int]:
        """Paginated gap list filtered by status.

        Returns:
            ``(items, total)`` ordered by ``ask_count`` descending.
        """
