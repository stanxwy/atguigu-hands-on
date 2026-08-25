"""SQLAlchemy adapter for IdentityRepository (SPEC §9.1 SqlIdentityRepository)."""

from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

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

    def get_user_by_id(self, user_id: str) -> User | None:
        with self._session_factory() as session:
            return session.scalar(
                select(User)
                .options(selectinload(User.department))
                .where(User.id == user_id)
            )

    def list_users(
        self,
        *,
        keyword: str | None = None,
        department_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        page = max(1, page)
        page_size = max(1, page_size)
        conditions = []
        if keyword:
            like = f"%{keyword}%"
            conditions.append(
                or_(User.username.ilike(like), User.display_name.ilike(like))
            )
        if department_id:
            conditions.append(User.department_id == department_id)

        with self._session_factory() as session:
            count_stmt = select(func.count()).select_from(User)
            if conditions:
                count_stmt = count_stmt.where(*conditions)
            total = session.scalar(count_stmt) or 0

            stmt = select(User).options(selectinload(User.department))
            if conditions:
                stmt = stmt.where(*conditions)
            items = list(
                session.scalars(
                    stmt.order_by(User.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            return items, total

    def delete_user(self, user_id: str) -> bool:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return False
            session.delete(user)
            session.commit()
            return True

    def list_roles(self) -> list[Role]:
        with self._session_factory() as session:
            return list(session.scalars(select(Role).order_by(Role.created_at)))

    def get_role_by_id(self, role_id: str) -> Role | None:
        with self._session_factory() as session:
            return session.get(Role, role_id)

    def get_role_by_code(self, role_code: str) -> Role | None:
        with self._session_factory() as session:
            return session.scalar(select(Role).where(Role.role_code == role_code))

    def list_departments(self) -> list[Department]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Department).order_by(
                        Department.sort_order, Department.created_at
                    )
                )
            )

    def get_department_by_id(self, department_id: str) -> Department | None:
        with self._session_factory() as session:
            return session.get(Department, department_id)

    def create_department(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        leader_id: str | None = None,
        sort_order: int = 0,
    ) -> Department:
        with self._session_factory() as session:
            department = Department(
                name=name,
                parent_id=parent_id,
                leader_id=leader_id,
                sort_order=sort_order,
            )
            session.add(department)
            session.commit()
            return department

    def update_department(
        self,
        department_id: str,
        *,
        name: str | None = None,
        parent_id: str | None = None,
        leader_id: str | None = None,
        sort_order: int | None = None,
    ) -> Department | None:
        with self._session_factory() as session:
            department = session.get(Department, department_id)
            if department is None:
                return None

            if name is not None:
                department.name = name
            if parent_id is not None:
                department.parent_id = parent_id
            if leader_id is not None:
                department.leader_id = leader_id
            if sort_order is not None:
                department.sort_order = sort_order

            session.commit()
            return department

    def delete_department(self, department_id: str) -> bool:
        with self._session_factory() as session:
            department = session.get(Department, department_id)
            if department is None:
                return False

            child_count = session.scalar(
                select(func.count())
                .select_from(Department)
                .where(Department.parent_id == department_id)
            ) or 0
            if child_count > 0:
                return False

            session.delete(department)
            session.commit()
            return True
