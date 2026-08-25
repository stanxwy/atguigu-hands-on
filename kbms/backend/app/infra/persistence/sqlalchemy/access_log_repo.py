"""SQLAlchemy adapter for AccessLogRepository (SPEC §9.1 SqlAccessLogRepository)."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models.entities import QaAccessLog
from app.domain.ports.access_log_repository import AccessLogRepository


class SqlAccessLogRepository(AccessLogRepository):
    """SQLAlchemy implementation of the QA access-log repository."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

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
        if total_tokens is None and (prompt_tokens is not None or completion_tokens is not None):
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

        log = QaAccessLog(
            session_id=session_id,
            question=question,
            answer=answer,
            user_id=user_id,
            recalled_unit_ids_json=recalled_unit_ids,
            authorized_unit_ids_json=authorized_unit_ids,
            unauthorized_unit_ids_json=unauthorized_unit_ids,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            response_time_ms=response_time_ms,
        )
        with self._session_factory() as session:
            session.add(log)
            session.commit()
            return log

    def aggregate_metrics(self, from_time: datetime, to_time: datetime) -> dict[str, Any]:
        with self._session_factory() as session:
            row = session.execute(
                select(
                    func.count(QaAccessLog.id),
                    func.count(func.distinct(QaAccessLog.user_id)),
                    func.coalesce(func.sum(QaAccessLog.prompt_tokens), 0),
                    func.coalesce(func.sum(QaAccessLog.completion_tokens), 0),
                    func.coalesce(func.sum(QaAccessLog.total_tokens), 0),
                    func.avg(QaAccessLog.response_time_ms),
                ).where(
                    QaAccessLog.created_at >= from_time,
                    QaAccessLog.created_at <= to_time,
                )
            ).one()

        return {
            "total_visits": int(row[0]),
            "unique_users": int(row[1]),
            "total_prompt_tokens": int(row[2]),
            "total_completion_tokens": int(row[3]),
            "total_tokens": int(row[4]),
            "avg_response_time_ms": round(float(row[5]), 2) if row[5] is not None else None,
        }

    def aggregate_rankings(
        self, from_time: datetime, to_time: datetime, limit: int = 10
    ) -> dict[str, Any]:
        limit = max(1, limit)
        with self._session_factory() as session:
            question_rows = session.execute(
                select(
                    QaAccessLog.question,
                    func.count(QaAccessLog.id).label("ask_count"),
                )
                .where(
                    QaAccessLog.created_at >= from_time,
                    QaAccessLog.created_at <= to_time,
                )
                .group_by(QaAccessLog.question)
                .order_by(func.count(QaAccessLog.id).desc())
                .limit(limit)
            ).all()

            # 单元排行基于 authorized_unit_ids_json（JSON 数组），跨方言无法用一条
            # SQL 稳定 unnest，故在 Python 侧统计（POC 规模下开销可忽略）。
            unit_id_rows = session.scalars(
                select(QaAccessLog.authorized_unit_ids_json).where(
                    QaAccessLog.created_at >= from_time,
                    QaAccessLog.created_at <= to_time,
                    QaAccessLog.authorized_unit_ids_json.is_not(None),
                )
            ).all()

        unit_counter: dict[str, int] = {}
        for ids in unit_id_rows:
            if isinstance(ids, list):
                for unit_id in ids:
                    if unit_id:
                        unit_counter[unit_id] = unit_counter.get(unit_id, 0) + 1

        top_units = sorted(unit_counter.items(), key=lambda kv: kv[1], reverse=True)[:limit]

        return {
            "questions": [
                {"question": q, "ask_count": int(c)} for q, c in question_rows
            ],
            "units": [
                {"unit_id": uid, "hit_count": count} for uid, count in top_units
            ],
        }
