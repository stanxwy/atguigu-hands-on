"""SQLAlchemy adapter for IdentityRepository (SPEC §9.1 SqlIdentityRepository)."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models.entities import Department, Role, RolePermission, User, UserRole
from app.domain.ports.identity_repository import IdentityRepository


class SqlIdentityRepository(IdentityRepository):
    """SQLAlchemy implementation of the identity & organization repository."""

    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def find_user_by_username(self, username: str) -> User | None:
        with self._session_factory() as session:
            return session.scalar(select(User).where(User.username == username))

    def get_user_roles(self, user_id: str) -> list[Role]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Role)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user_id)
                )
            )

    def get_role_permissions(self, role_id: str) -> list[RolePermission]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(RolePermission).where(RolePermission.role_id == role_id)
                )
            )

    def list_departments_tree(self) -> list[dict[str, Any]]:
        with self._session_factory() as session:
            departments = list(
                session.scalars(
                    select(Department).order_by(Department.sort_order, Department.created_at)
                )
            )

        by_id: dict[str, dict[str, Any]] = {
            d.id: {
                "id": d.id,
                "parent_id": d.parent_id,
                "name": d.name,
                "leader_id": d.leader_id,
                "sort_order": d.sort_order,
                "children": [],
            }
            for d in departments
        }
        roots: list[dict[str, Any]] = []
        for node in by_id.values():
            parent_id = node["parent_id"]
            if parent_id and parent_id in by_id:
                by_id[parent_id]["children"].append(node)
            else:
                roots.append(node)
        return roots

    def create_user(
        self,
        username: str,
        password_hash: str,
        display_name: str,
        department_id: str | None = None,
        status: int = 1,
        role_ids: list[str] | None = None,
    ) -> User:
        with self._session_factory() as session:
            user = User(
                username=username,
                password_hash=password_hash,
                display_name=display_name,
                department_id=department_id,
                status=status,
            )
            session.add(user)
            session.flush()  # assigns user.id before binding roles
            if role_ids:
                for role_id in role_ids:
                    session.add(UserRole(user_id=user.id, role_id=role_id))
            session.commit()
            return user

    def update_user(
        self,
        user_id: str,
        *,
        password_hash: str | None = None,
        display_name: str | None = None,
        department_id: str | None = None,
        status: int | None = None,
        role_ids: list[str] | None = None,
    ) -> User | None:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return None

            if password_hash is not None:
                user.password_hash = password_hash
            if display_name is not None:
                user.display_name = display_name
            if department_id is not None:
                user.department_id = department_id
            if status is not None:
                user.status = status

            if role_ids is not None:
                session.execute(delete(UserRole).where(UserRole.user_id == user_id))
                for role_id in role_ids:
                    session.add(UserRole(user_id=user_id, role_id=role_id))

            session.commit()
            return user

    def create_role(
        self, role_name: str, role_code: str, description: str | None = None
    ) -> Role:
        with self._session_factory() as session:
            role = Role(role_name=role_name, role_code=role_code, description=description)
            session.add(role)
            session.commit()
            return role

    def replace_role_permissions(
        self, role_id: str, permissions: list[tuple[str, str]]
    ) -> None:
        with self._session_factory() as session:
            session.execute(
                delete(RolePermission).where(RolePermission.role_id == role_id)
            )
            for code, perm_type in permissions:
                session.add(
                    RolePermission(role_id=role_id, permission_code=code, permission_type=perm_type)
                )
            session.commit()
