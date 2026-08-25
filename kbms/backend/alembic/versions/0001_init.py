"""0001_init — create the 10 KBMS relational tables (SPEC §2.1).

Revision ID: 0001
Revises:
Create Date: 2026-08-25

Notes:
* UUID PKs are ``String(36)`` (uuid4 generated Python-side) for cross-dialect
  portability (PostgreSQL + SQLite), per SPEC §2.2.
* JSONB columns use ``JSON().with_variant(JSONB, "postgresql")``.
* ``users.department_id`` ↔ ``departments.leader_id`` form a circular FK. Both
  are declared inline; ``departments.leader_id`` carries ``use_alter=True`` so
  PostgreSQL defers it via ALTER (SQLite inlines it directly, which it supports
  because CREATE TABLE may reference not-yet-created tables).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# JSONB on PostgreSQL, generic JSON elsewhere (SQLite in dev/test).
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    op.create_table(
        "departments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "leader_id",
            sa.String(length=36),
            sa.ForeignKey(
                "users.id",
                name="fk_departments_leader_id_users",
                ondelete="SET NULL",
                use_alter=True,
            ),
            nullable=True,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_departments_parent", "departments", ["parent_id"])
    op.create_index("idx_departments_leader", "departments", ["leader_id"])

    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column(
            "department_id",
            sa.String(length=36),
            sa.ForeignKey("departments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username", name="uk_users_username"),
    )
    op.create_index("idx_users_department", "users", ["department_id"])

    # ------------------------------------------------------------------ #
    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("role_name", sa.String(length=64), nullable=False),
        sa.Column("role_code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("role_code", name="uk_roles_code"),
    )

    # ------------------------------------------------------------------ #
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.String(length=36),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "role_id", name="uk_user_roles_user_role"),
    )
    op.create_index("idx_user_roles_role", "user_roles", ["role_id"])

    # ------------------------------------------------------------------ #
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "role_id",
            sa.String(length=36),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("permission_code", sa.String(length=64), nullable=False),
        sa.Column("permission_type", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint(
            "role_id", "permission_code", "permission_type",
            name="uk_role_permissions_role_code_type",
        ),
    )
    op.create_index("idx_rp_role", "role_permissions", ["role_id"])

    # ------------------------------------------------------------------ #
    op.create_table(
        "knowledge_units",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("unit_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("source_file_name", sa.String(length=255), nullable=True),
        sa.Column("file_type", sa.String(length=16), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column(
            "creator_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("unit_code", name="uk_ku_unit_code"),
    )
    op.create_index("idx_ku_status", "knowledge_units", ["status"])
    op.create_index("idx_ku_category", "knowledge_units", ["category"])
    op.create_index("idx_ku_creator", "knowledge_units", ["creator_id"])
    op.create_index("idx_ku_title", "knowledge_units", ["title"])

    # ------------------------------------------------------------------ #
    op.create_table(
        "unit_permissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "unit_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_units.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("unit_id", "target_type", "target_id", name="uk_unit_permissions_unit_target"),
    )
    op.create_index("idx_up_target", "unit_permissions", ["target_type", "target_id"])

    # ------------------------------------------------------------------ #
    op.create_table(
        "qa_access_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("recalled_unit_ids_json", JSON_TYPE, nullable=True),
        sa.Column("authorized_unit_ids_json", JSON_TYPE, nullable=True),
        sa.Column("unauthorized_unit_ids_json", JSON_TYPE, nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_qal_created", "qa_access_logs", ["created_at"])
    op.create_index("idx_qal_user", "qa_access_logs", ["user_id"])
    op.create_index("idx_qal_session", "qa_access_logs", ["session_id"])
    op.create_index("idx_qal_user_created", "qa_access_logs", ["user_id", "created_at"])

    # ------------------------------------------------------------------ #
    op.create_table(
        "faqs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("question", sa.String(length=1024), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column(
            "related_unit_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_type", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending_review"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "reviewer_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_faq_status", "faqs", ["status"])
    op.create_index("idx_faq_category", "faqs", ["category"])
    op.create_index("idx_faq_hit", "faqs", ["hit_count"])

    # ------------------------------------------------------------------ #
    op.create_table(
        "knowledge_gaps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("question_pattern", sa.Text(), nullable=False),
        sa.Column("sample_questions_json", JSON_TYPE, nullable=True),
        sa.Column("ask_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_asked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="unresolved"),
        sa.Column(
            "resolved_unit_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_gap_status", "knowledge_gaps", ["status"])
    op.create_index("idx_gap_ask", "knowledge_gaps", ["ask_count"])
    op.create_index("idx_gap_last", "knowledge_gaps", ["last_asked_at"])


def downgrade() -> None:
    # 按创建逆序 drop_table；SQLite 允许 DROP 被其他表外键引用的表（且默认不
    # 强制外键），PostgreSQL 下 use_alter 的环回外键随 departments 表一并删除。
    op.drop_table("knowledge_gaps")
    op.drop_table("faqs")
    op.drop_table("qa_access_logs")
    op.drop_table("unit_permissions")
    op.drop_table("knowledge_units")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("departments")
