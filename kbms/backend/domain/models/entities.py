"""SQLAlchemy ORM models for the KBMS relational data layer (SPEC §2).

All 10 tables from SPEC §2.1 are defined here as SQLAlchemy 2.0 style
(``DeclarativeBase`` + ``Mapped``/``mapped_column``) models. Field names,
types, nullability, defaults, unique constraints, indexes and foreign keys
(including ``ON DELETE`` behaviour) follow SPEC §2.1 / §2.3 exactly.

Portability notes
-----------------
* Primary keys are UUIDs stored as ``String(36)`` (``uuid4`` generated
  Python-side), matching SPEC §2.2's "string UUID" decision and working
  identically on PostgreSQL and SQLite (dev/test) without any dialect SQL.
* JSONB columns use ``JSON().with_variant(JSONB, "postgresql")`` so the same
  model maps to native JSONB on PostgreSQL and generic JSON on SQLite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Return the current timezone-aware UTC datetime (SPEC §8: ISO 8601 UTC)."""
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    """Generate a new UUID (uuid4) as a string — SPEC §2.2 ID strategy."""
    return str(uuid4())


#: JSONB on PostgreSQL, generic JSON elsewhere (SQLite in dev/test).
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    """Declarative base shared by all KBMS relational models."""


class User(Base):
    """用户表（users）— SPEC §2.1."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uk_users_username"),
        Index("idx_users_department", "department_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    department_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # 用户 → 部门（many-to-one）；反向为 Department.members
    department: Mapped[Department | None] = relationship(
        back_populates="members", foreign_keys=[department_id]
    )
    # 用户作为部门负责人的部门集合（one-to-many）
    led_departments: Mapped[list[Department]] = relationship(
        back_populates="leader", foreign_keys="Department.leader_id"
    )
    created_units: Mapped[list[KnowledgeUnit]] = relationship(back_populates="creator")
    reviewed_faqs: Mapped[list[Faq]] = relationship(back_populates="reviewer")
    access_logs: Mapped[list[QaAccessLog]] = relationship(back_populates="user")


class Department(Base):
    """部门表（departments）— SPEC §2.1."""

    __tablename__ = "departments"
    __table_args__ = (
        Index("idx_departments_parent", "parent_id"),
        Index("idx_departments_leader", "leader_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # 根节点 parent_id 为 NULL（等价需求「0 为根」语义，SPEC §2.2）。
    # SPEC 未规定 parent_id 的 ON DELETE 行为，故沿用数据库默认（NO ACTION）。
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("departments.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    leader_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # 自引用邻接表：parent / children（SPEC §2.4 ER）
    parent: Mapped[Department | None] = relationship(
        back_populates="children", remote_side="Department.id"
    )
    children: Mapped[list[Department]] = relationship(back_populates="parent")
    leader: Mapped[User | None] = relationship(
        back_populates="led_departments", foreign_keys=[leader_id]
    )
    members: Mapped[list[User]] = relationship(
        back_populates="department", foreign_keys="User.department_id"
    )


class Role(Base):
    """角色表（roles）— SPEC §2.1."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("role_code", name="uk_roles_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role_code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    permissions: Mapped[list[RolePermission]] = relationship(back_populates="role")


class UserRole(Base):
    """用户-角色关联表（user_roles）— SPEC §2.1."""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uk_user_roles_user_role"),
        Index("idx_user_roles_role", "role_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    # 关联对象模式：仅暴露单向关系，避免 secondary 表额外列冲突。
    user: Mapped[User] = relationship("User")
    role: Mapped[Role] = relationship("Role")


class RolePermission(Base):
    """角色权限表（role_permissions）— SPEC §2.1."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "role_id", "permission_code", "permission_type", name="uk_role_permissions_role_code_type"
        ),
        Index("idx_rp_role", "role_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_code: Mapped[str] = mapped_column(String(64), nullable=False)
    permission_type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    role: Mapped[Role] = relationship(back_populates="permissions")


class KnowledgeUnit(Base):
    """知识单元表（knowledge_units）— SPEC §2.1."""

    __tablename__ = "knowledge_units"
    __table_args__ = (
        UniqueConstraint("unit_code", name="uk_ku_unit_code"),
        Index("idx_ku_status", "status"),
        Index("idx_ku_category", "category"),
        Index("idx_ku_creator", "creator_id"),
        Index("idx_ku_title", "title"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    unit_code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # 仅 published 参与召回（SPEC §8）
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    creator_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    creator: Mapped[User | None] = relationship(back_populates="created_units", foreign_keys=[creator_id])
    permissions: Mapped[list[UnitPermission]] = relationship(back_populates="unit")
    faqs: Mapped[list[Faq]] = relationship(back_populates="related_unit")
    gaps: Mapped[list[KnowledgeGap]] = relationship(back_populates="resolved_unit")


class UnitPermission(Base):
    """知识单元数据权限表（unit_permissions）— SPEC §2.1."""

    __tablename__ = "unit_permissions"
    __table_args__ = (
        UniqueConstraint("unit_id", "target_type", "target_id", name="uk_unit_permissions_unit_target"),
        Index("idx_up_target", "target_type", "target_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_units.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # global 时为 NULL/忽略（SPEC §2.1）
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    unit: Mapped[KnowledgeUnit] = relationship(back_populates="permissions")


class QaAccessLog(Base):
    """问答访问日志表（qa_access_logs）— SPEC §2.1（保留 180 天，见 §2.2）."""

    __tablename__ = "qa_access_logs"
    __table_args__ = (
        Index("idx_qal_created", "created_at"),
        Index("idx_qal_user", "user_id"),
        Index("idx_qal_session", "session_id"),
        Index("idx_qal_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    recalled_unit_ids_json: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    authorized_unit_ids_json: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    unauthorized_unit_ids_json: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    user: Mapped[User | None] = relationship(back_populates="access_logs")


class Faq(Base):
    """FAQ 表（faqs）— SPEC §2.1."""

    __tablename__ = "faqs"
    __table_args__ = (
        Index("idx_faq_status", "status"),
        Index("idx_faq_category", "category"),
        Index("idx_faq_hit", "hit_count"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    question: Mapped[str] = mapped_column(String(1024), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_unit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_units.id", ondelete="SET NULL"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="manual", server_default="manual")
    # 三态：pending_review / published / rejected（SPEC §2.1）
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending_review", server_default="pending_review"
    )
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    reviewer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    related_unit: Mapped[KnowledgeUnit | None] = relationship(
        back_populates="faqs", foreign_keys=[related_unit_id]
    )
    reviewer: Mapped[User | None] = relationship(
        back_populates="reviewed_faqs", foreign_keys=[reviewer_id]
    )


class KnowledgeGap(Base):
    """知识缺口表（knowledge_gaps）— SPEC §2.1."""

    __tablename__ = "knowledge_gaps"
    __table_args__ = (
        Index("idx_gap_status", "status"),
        Index("idx_gap_ask", "ask_count"),
        Index("idx_gap_last", "last_asked_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    question_pattern: Mapped[str] = mapped_column(Text, nullable=False)
    sample_questions_json: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True)
    ask_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    last_asked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 三态：unresolved / resolved / ignored（SPEC §2.1）
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="unresolved", server_default="unresolved")
    resolved_unit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_units.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    resolved_unit: Mapped[KnowledgeUnit | None] = relationship(
        back_populates="gaps", foreign_keys=[resolved_unit_id]
    )
