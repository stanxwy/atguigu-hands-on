"""Model contract tests (SPEC §2.1): the 10 ORM tables, tablenames, key columns
and ``Base.metadata.create_all`` on in-memory SQLite.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect

from app.domain.models.entities import (
    Base,
    Department,
    Faq,
    KnowledgeGap,
    KnowledgeUnit,
    QaAccessLog,
    Role,
    RolePermission,
    UnitPermission,
    User,
    UserRole,
)

ALL_TABLES = {
    "users",
    "departments",
    "roles",
    "user_roles",
    "role_permissions",
    "knowledge_units",
    "unit_permissions",
    "qa_access_logs",
    "faqs",
    "knowledge_gaps",
}

ALL_MODELS = [
    User,
    Department,
    Role,
    UserRole,
    RolePermission,
    KnowledgeUnit,
    UnitPermission,
    QaAccessLog,
    Faq,
    KnowledgeGap,
]


def test_exactly_ten_models_registered_on_metadata():
    assert set(Base.metadata.tables.keys()) == ALL_TABLES


@pytest.mark.parametrize("model", ALL_MODELS)
def test_model_has_table(model):
    assert model.__tablename__ in ALL_TABLES


def test_tablename_contract():
    assert User.__tablename__ == "users"
    assert Department.__tablename__ == "departments"
    assert Role.__tablename__ == "roles"
    assert UserRole.__tablename__ == "user_roles"
    assert RolePermission.__tablename__ == "role_permissions"
    assert KnowledgeUnit.__tablename__ == "knowledge_units"
    assert UnitPermission.__tablename__ == "unit_permissions"
    assert QaAccessLog.__tablename__ == "qa_access_logs"
    assert Faq.__tablename__ == "faqs"
    assert KnowledgeGap.__tablename__ == "knowledge_gaps"


def test_users_key_columns():
    cols = {c.name for c in User.__table__.columns}
    assert {
        "id",
        "username",
        "password_hash",
        "display_name",
        "department_id",
        "status",
        "created_at",
        "updated_at",
    } <= cols


def test_unit_permissions_target_type():
    cols = {c.name for c in UnitPermission.__table__.columns}
    assert {"unit_id", "target_type", "target_id"} <= cols


def test_qa_access_logs_token_columns():
    cols = {c.name for c in QaAccessLog.__table__.columns}
    assert {"prompt_tokens", "completion_tokens", "total_tokens", "response_time_ms"} <= cols


def test_faqs_status_column():
    cols = {c.name for c in Faq.__table__.columns}
    assert "status" in cols
    assert {"question", "answer", "hit_count", "reviewer_id", "reviewed_at"} <= cols


def test_knowledge_gaps_columns():
    cols = {c.name for c in KnowledgeGap.__table__.columns}
    assert {"question_pattern", "sample_questions_json", "ask_count", "status", "resolved_unit_id"} <= cols


def test_create_all_on_in_memory_sqlite():
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        insp = inspect(engine)
        assert set(insp.get_table_names()) == ALL_TABLES
    finally:
        engine.dispose()
