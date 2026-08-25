"""Repository adapter CRUD tests (SPEC §9.1) against in-memory SQLite.

All five SQLAlchemy adapters are exercised with a ``sessionmaker`` bound to a
single in-memory SQLite connection (``StaticPool`` so the schema survives
across the repository's per-call session boundaries).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.models.entities import Base, KnowledgeUnit
from app.infra.persistence.sqlalchemy.access_log_repo import SqlAccessLogRepository
from app.infra.persistence.sqlalchemy.faq_repo import SqlFaqRepository
from app.infra.persistence.sqlalchemy.gap_repo import SqlGapRepository
from app.infra.persistence.sqlalchemy.identity_repo import SqlIdentityRepository
from app.infra.persistence.sqlalchemy.knowledge_repo import SqlKnowledgeRepository


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def identity_repo(session_factory):
    return SqlIdentityRepository(session_factory)


@pytest.fixture()
def knowledge_repo(session_factory):
    return SqlKnowledgeRepository(session_factory)


@pytest.fixture()
def access_log_repo(session_factory):
    return SqlAccessLogRepository(session_factory)


@pytest.fixture()
def faq_repo(session_factory):
    return SqlFaqRepository(session_factory)


@pytest.fixture()
def gap_repo(session_factory):
    return SqlGapRepository(session_factory)


# --------------------------------------------------------------------------- #
# IdentityRepository
# --------------------------------------------------------------------------- #
def test_identity_create_user_and_find_by_username(identity_repo):
    user = identity_repo.create_user(
        username="alice",
        password_hash="hashed",
        display_name="Alice",
    )
    assert user.id

    found = identity_repo.find_user_by_username("alice")
    assert found is not None
    assert found.id == user.id
    assert found.display_name == "Alice"

    assert identity_repo.find_user_by_username("nobody") is None


def test_identity_user_roles_and_role_permissions(identity_repo):
    role = identity_repo.create_role("系统管理员", "sys_admin", "全部权限")
    user = identity_repo.create_user(
        username="bob",
        password_hash="hashed",
        display_name="Bob",
        role_ids=[role.id],
    )

    roles = identity_repo.get_user_roles(user.id)
    assert [r.role_code for r in roles] == ["sys_admin"]

    identity_repo.replace_role_permissions(
        role.id, [("knowledge:unit", "read"), ("ai", "ai_access")]
    )
    perms = identity_repo.get_role_permissions(role.id)
    assert {(p.permission_code, p.permission_type) for p in perms} == {
        ("knowledge:unit", "read"),
        ("ai", "ai_access"),
    }


def test_identity_department_tree(identity_repo):
    # departments are created directly through the ORM session in the adapter
    # via a raw session — here we exercise create_user + list_departments_tree
    # using the factory bound session.
    from app.domain.models.entities import Department

    with identity_repo._session_factory() as s:
        parent = Department(name="总部", parent_id=None, sort_order=0)
        s.add(parent)
        s.flush()
        s.add(Department(name="研发部", parent_id=parent.id, sort_order=1))
        s.commit()

    tree = identity_repo.list_departments_tree()
    assert len(tree) == 1
    assert tree[0]["name"] == "总部"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["name"] == "研发部"


# --------------------------------------------------------------------------- #
# KnowledgeRepository
# --------------------------------------------------------------------------- #
def _make_unit(**overrides) -> KnowledgeUnit:
    defaults = dict(
        unit_code="KU-20260825-000001",
        title="员工入职流程说明",
        content="# 员工入职流程\n\n1. 提交入职材料",
        status="draft",
    )
    defaults.update(overrides)
    return KnowledgeUnit(**defaults)


def test_knowledge_create_list_get(knowledge_repo):
    unit = knowledge_repo.create_unit(_make_unit())
    assert unit.id

    items, total = knowledge_repo.list_units(page=1, page_size=20)
    assert total == 1
    assert items[0].id == unit.id

    got = knowledge_repo.get_unit(unit.id)
    assert got is not None
    assert got.title == "员工入职流程说明"

    assert knowledge_repo.get_unit("missing-id") is None


def test_knowledge_permissions_replace_and_get(knowledge_repo):
    unit = knowledge_repo.create_unit(_make_unit())

    knowledge_repo.replace_unit_permissions(
        unit.id, [("global", None), ("role", "role-123"), ("user", "user-456")]
    )
    perms = knowledge_repo.get_unit_permissions(unit.id)
    assert {(p.target_type, p.target_id) for p in perms} == {
        ("global", None),
        ("role", "role-123"),
        ("user", "user-456"),
    }

    # replacement semantics: second call wipes previous rows
    knowledge_repo.replace_unit_permissions(unit.id, [("user", "user-999")])
    perms = knowledge_repo.get_unit_permissions(unit.id)
    assert [(p.target_type, p.target_id) for p in perms] == [("user", "user-999")]


def test_knowledge_soft_delete_units(knowledge_repo):
    u1 = knowledge_repo.create_unit(_make_unit(unit_code="KU-1", title="A"))
    u2 = knowledge_repo.create_unit(_make_unit(unit_code="KU-2", title="B"))

    count = knowledge_repo.soft_delete_units([u1.id, u2.id])
    assert count == 2
    assert knowledge_repo.get_unit(u1.id).status == "offline"
    assert knowledge_repo.get_unit(u2.id).status == "offline"

    assert knowledge_repo.soft_delete_units([]) == 0


# --------------------------------------------------------------------------- #
# AccessLogRepository
# --------------------------------------------------------------------------- #
def test_access_log_append_and_metrics(access_log_repo):
    access_log_repo.append_log(
        session_id="s1",
        question="how to onboard?",
        answer="do X",
        user_id="u1",
        prompt_tokens=10,
        completion_tokens=5,
        response_time_ms=120,
    )
    # total_tokens defaults to prompt + completion when omitted
    access_log_repo.append_log(
        session_id="s2",
        question="expense?",
        answer="do Y",
        user_id="u1",
        prompt_tokens=20,
        completion_tokens=10,
        response_time_ms=80,
    )

    from_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    to_time = datetime(2100, 1, 1, tzinfo=timezone.utc)
    metrics = access_log_repo.aggregate_metrics(from_time, to_time)

    assert metrics["total_visits"] == 2
    assert metrics["unique_users"] == 1
    assert metrics["total_prompt_tokens"] == 30
    assert metrics["total_completion_tokens"] == 15
    assert metrics["total_tokens"] == 45
    assert metrics["avg_response_time_ms"] == 100.0


def test_access_log_rankings(access_log_repo):
    access_log_repo.append_log(
        session_id="s1",
        question="how to onboard?",
        user_id="u1",
        authorized_unit_ids=["unit-a", "unit-b"],
    )
    access_log_repo.append_log(
        session_id="s2",
        question="how to onboard?",
        user_id="u2",
        authorized_unit_ids=["unit-a"],
    )
    access_log_repo.append_log(
        session_id="s3",
        question="expense?",
        user_id="u3",
        authorized_unit_ids=["unit-c"],
    )

    from_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    to_time = datetime(2100, 1, 1, tzinfo=timezone.utc)
    rankings = access_log_repo.aggregate_rankings(from_time, to_time, limit=10)

    qcount = {q["question"]: q["ask_count"] for q in rankings["questions"]}
    assert qcount == {"how to onboard?": 2, "expense?": 1}

    ucount = {u["unit_id"]: u["hit_count"] for u in rankings["units"]}
    assert ucount == {"unit-a": 2, "unit-b": 1, "unit-c": 1}


# --------------------------------------------------------------------------- #
# FaqRepository
# --------------------------------------------------------------------------- #
def test_faq_create_review_list(faq_repo):
    faq = faq_repo.create_faq(question="如何报销？", answer="提供发票", category="财务")
    assert faq.status == "pending_review"

    reviewed = faq_repo.review_faq(faq.id, action="approve", reviewer_id="rv1")
    assert reviewed.status == "published"
    assert reviewed.reviewer_id == "rv1"
    assert reviewed.reviewed_at is not None

    items, total = faq_repo.list_faqs(status="published")
    assert total == 1
    assert items[0].id == faq.id

    published = faq_repo.get_published_faqs()
    assert [f.id for f in published] == [faq.id]


def test_faq_reject_and_edited_answer(faq_repo):
    faq = faq_repo.create_faq(question="Q", answer="old")
    rejected = faq_repo.review_faq(faq.id, action="reject", reviewer_id="rv2")
    assert rejected.status == "rejected"

    faq2 = faq_repo.create_faq(question="Q2", answer="old")
    approved = faq_repo.review_faq(
        faq2.id, action="approve", reviewer_id="rv2", edited_answer="new answer"
    )
    assert approved.status == "published"
    assert approved.answer == "new answer"


# --------------------------------------------------------------------------- #
# GapRepository
# --------------------------------------------------------------------------- #
def test_gap_upsert_and_list(gap_repo):
    g1 = gap_repo.upsert_gap(question_pattern="如何申请报销？", ask_count=1)
    assert g1.ask_count == 1

    # second upsert on the same pattern increments ask_count
    g2 = gap_repo.upsert_gap(
        question_pattern="如何申请报销？",
        ask_count=2,
        sample_questions=["报销需要什么？"],
    )
    assert g2.id == g1.id
    assert g2.ask_count == 3
    assert g2.sample_questions_json == ["报销需要什么？"]

    items, total = gap_repo.list_gaps(status="unresolved")
    assert total == 1
    assert items[0].question_pattern == "如何申请报销？"
    assert items[0].ask_count == 3


def test_gap_resolved_status_transition(gap_repo):
    gap = gap_repo.upsert_gap(question_pattern="某个未知问题", ask_count=5)
    updated = gap_repo.upsert_gap(
        question_pattern="某个未知问题",
        status="resolved",
        resolved_unit_id="unit-1",
    )
    assert updated.status == "resolved"
    assert updated.resolved_unit_id == "unit-1"
    assert updated.ask_count == 6

    items, total = gap_repo.list_gaps(status="resolved")
    assert total == 1
