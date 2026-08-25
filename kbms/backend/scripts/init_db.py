"""Initialize the KBMS relational database: create tables + seed baseline data.

Usage (from ``backend/``)::

    python scripts/init_db.py

Idempotent: seeding is skipped when the ``admin`` user already exists. Uses the
ORM ``Base.metadata.create_all`` (the versioned path is ``alembic upgrade head``).
"""

from __future__ import annotations

import sys
from pathlib import Path

import bcrypt

# Make the backend project root importable so `app.*` resolves when this script
# is invoked directly (namespace package, no __init__.py).
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import select  # noqa: E402

from app.domain.models.entities import (  # noqa: E402
    Base,
    Department,
    KnowledgeUnit,
    Role,
    RolePermission,
    UnitPermission,
    User,
    UserRole,
)
from app.infra.config.settings import get_settings  # noqa: E402
from app.infra.persistence.sqlalchemy.base import (  # noqa: E402
    create_engine_from_settings,
    create_session_factory,
)

#: Admin account seed credentials (change in production).
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_DISPLAY_NAME = "系统管理员"

#: Default roles and their permission sets (SPEC §3.1 / §8 RBAC).
#: Keys are role_code; values are (role_name, description).
DEFAULT_ROLES: dict[str, tuple[str, str]] = {
    "sys_admin": ("系统管理员", "拥有全部操作权限"),
    "knowledge_admin": ("知识管理员", "知识单元/看板/沉淀管理权限"),
    "user": ("普通用户", "知识检索与 AI 问答权限"),
}

#: Permission matrix: role_code -> list[(permission_code, permission_type)].
ROLE_PERMISSIONS: dict[str, list[tuple[str, str]]] = {
    "sys_admin": [
        ("org:user", "create"),
        ("org:user", "read"),
        ("org:user", "update"),
        ("org:user", "delete"),
        ("org:role", "read"),
        ("org:role", "create"),
        ("org:role", "update"),
        ("knowledge:unit", "create"),
        ("knowledge:unit", "read"),
        ("knowledge:unit", "update"),
        ("knowledge:unit", "delete"),
        ("dashboard", "read"),
        ("settlement:faq", "read"),
        ("settlement:faq", "update"),
        ("settlement:gap", "read"),
        ("ai", "ai_access"),
    ],
    "knowledge_admin": [
        ("knowledge:unit", "create"),
        ("knowledge:unit", "read"),
        ("knowledge:unit", "update"),
        ("knowledge:unit", "delete"),
        ("dashboard", "read"),
        ("settlement:faq", "read"),
        ("settlement:faq", "update"),
        ("settlement:gap", "read"),
        ("ai", "ai_access"),
    ],
    "user": [
        ("knowledge:unit", "read"),
        ("dashboard", "read"),
        ("ai", "ai_access"),
    ],
}


def _seed_org(session) -> tuple[Department, dict[str, Role], User]:
    """Create the root department, default roles, admin user and bindings."""
    department = Department(name="总部", parent_id=None, sort_order=0)
    session.add(department)
    session.flush()  # assign department.id

    roles: dict[str, Role] = {}
    for code, (name, desc) in DEFAULT_ROLES.items():
        role = Role(role_name=name, role_code=code, description=desc)
        session.add(role)
        roles[code] = role
    session.flush()  # assign role ids

    for code, perms in ROLE_PERMISSIONS.items():
        for perm_code, perm_type in perms:
            session.add(
                RolePermission(
                    role_id=roles[code].id,
                    permission_code=perm_code,
                    permission_type=perm_type,
                )
            )

    password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin = User(
        username=ADMIN_USERNAME,
        password_hash=password_hash,
        display_name=ADMIN_DISPLAY_NAME,
        department_id=department.id,
        status=1,
    )
    session.add(admin)
    session.flush()  # assign admin.id

    session.add(UserRole(user_id=admin.id, role_id=roles["sys_admin"].id))
    return department, roles, admin


def _seed_knowledge(session, roles: dict[str, Role], admin: User) -> None:
    """Create example knowledge units and their data permissions."""
    unit1 = KnowledgeUnit(
        unit_code="KU-20260825-000001",
        title="员工入职流程说明",
        content="# 员工入职流程\n\n1. 提交入职材料\n2. 签订劳动合同\n3. 领取工牌与账号\n",
        summary="员工入职所需的材料与步骤说明",
        category="人力资源",
        source_file_name="onboarding.md",
        file_type="md",
        status="published",
        creator_id=admin.id,
    )
    unit2 = KnowledgeUnit(
        unit_code="KU-20260825-000002",
        title="费用报销制度",
        content="# 费用报销制度\n\n- 差旅费按实际发生报销\n- 需提供发票与审批单\n",
        summary="差旅与日常费用报销规则",
        category="财务",
        source_file_name="expense.md",
        file_type="md",
        status="published",
        creator_id=admin.id,
    )
    session.add_all([unit1, unit2])
    session.flush()

    # 数据权限：unit1 全局可见；unit2 仅 user 角色可见（OR 语义示例）
    session.add(UnitPermission(unit_id=unit1.id, target_type="global", target_id=None))
    session.add(UnitPermission(unit_id=unit2.id, target_type="role", target_id=roles["user"].id))


def main() -> None:
    """Create schema and seed data (idempotent)."""
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    Base.metadata.create_all(engine)

    session_factory = create_session_factory(engine)
    with session_factory() as session:
        existing_admin = session.scalar(select(User).where(User.username == ADMIN_USERNAME))
        if existing_admin is not None:
            print(f"Seeding skipped: user '{ADMIN_USERNAME}' already exists.")
            return

        department, roles, admin = _seed_org(session)
        _seed_knowledge(session, roles, admin)
        session.commit()

        print("Database initialized and seeded successfully:")
        print(f"  - department: {department.name} ({department.id})")
        print(f"  - roles: {', '.join(roles)}")
        print(f"  - admin user: {admin.username} / {ADMIN_PASSWORD} (change in production)")
        print("  - example knowledge_units: 2 + unit_permissions")


if __name__ == "__main__":
    main()
