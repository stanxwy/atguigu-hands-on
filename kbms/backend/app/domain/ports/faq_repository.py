"""FAQ repository port (SPEC §9.1 FaqRepository)."""

from abc import ABC, abstractmethod

from app.domain.models.entities import Faq


class FaqRepository(ABC):
    """Persistence port for faqs (candidates + review workflow)."""

    @abstractmethod
    def list_faqs(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Faq], int]:
        """Paginated FAQ list filtered by status/category.

        Returns:
            ``(items, total)`` ordered by ``created_at`` descending.
        """

    @abstractmethod
    def create_faq(
        self,
        *,
        question: str,
        answer: str,
        category: str | None = None,
        related_unit_id: str | None = None,
        source_type: str = "manual",
    ) -> Faq:
        """Create an FAQ candidate (default status ``pending_review``)."""

    @abstractmethod
    def review_faq(
        self,
        faq_id: str,
        *,
        action: str,
        reviewer_id: str,
        edited_answer: str | None = None,
    ) -> Faq | None:
        """Review an FAQ (SPEC §3.2 review endpoint).

        Args:
            faq_id: Target FAQ id.
            action: ``approve`` (→ ``published``) or ``reject`` (→ ``rejected``).
            reviewer_id: Reviewer user id.
            edited_answer: Optional revised answer applied on approve.

        Records ``reviewer_id``/``reviewed_at``; returns the updated ``Faq`` or
        ``None`` if not found.
        """

    @abstractmethod
    def get_published_faqs(self) -> list[Faq]:
        """Return all published FAQs (used to warm the FAQ hit cache)."""
