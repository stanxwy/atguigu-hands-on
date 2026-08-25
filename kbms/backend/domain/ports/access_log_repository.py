"""QA access-log repository port (SPEC §9.1 AccessLogRepository)."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.domain.models.entities import QaAccessLog


class AccessLogRepository(ABC):
    """Persistence port for qa_access_logs (append + dashboard aggregation)."""

    @abstractmethod
    def append_log(
        self,
        *,
        session_id: str,
        question: str,
        answer: str | None = None,
        user_id: str | None = None,
        recalled_unit_ids: list[str] | None = None,
        authorized_unit_ids: list[str] | None = None,
        unauthorized_unit_ids: list[str] | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        response_time_ms: int | None = None,
    ) -> QaAccessLog:
        """Append one QA access log row (SPEC §5.7 token/response-time口径).

        ``total_tokens`` defaults to ``prompt_tokens + completion_tokens`` when
        not provided; ``response_time_ms`` is server-side processing time only
        (excludes SSE streaming time).
        """

    @abstractmethod
    def aggregate_metrics(self, from_time: datetime, to_time: datetime) -> dict[str, Any]:
        """Aggregate dashboard metric-card values over ``[from_time, to_time]``.

        Returns:
            Dict with keys ``total_visits``, ``unique_users``,
            ``total_prompt_tokens``, ``total_completion_tokens``,
            ``total_tokens``, ``avg_response_time_ms``.
        """

    @abstractmethod
    def aggregate_rankings(
        self, from_time: datetime, to_time: datetime, limit: int = 10
    ) -> dict[str, Any]:
        """Aggregate high-frequency question & unit rankings.

        Returns:
            Dict with keys ``questions`` (``[{question, ask_count}]``) and
            ``units`` (``[{unit_id, hit_count}]``, derived from
            ``authorized_unit_ids_json``).
        """
