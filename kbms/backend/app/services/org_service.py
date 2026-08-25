"""Organization application service (SPEC §9.1 OrgService)."""

from __future__ import annotations

from app.domain.exceptions import BadRequestError, ConflictError, NotFoundError
from app.domain.ports.auth_port import PasswordHasher
from app.domain.ports.identity_repository import IdentityRepository


class OrgService:
    """User / role / department CRUD orchestration (SPEC §3.1)."""

    def __init__(self, identity_repo: IdentityRepository, password_hasher: PasswordHasher) -> None:
        self._repo = identity_repo
        self._password_hasher = password_hasher

    # ------------------------------------------------------------------ #
    # Departments
    # ------------------------------------------------------------------ #
    def list_departments_tree(self) -> list[dict]:
        """Return the full department tree (SPEC §3.1 ``GET /org/departments``)."""
        return self._repo.list_departments_tree()

    def create_department(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        leader_id: str | None = None,
        sort_order: int = 0,
    ) -> dict:
        if parent_id is not None and self._repo.get_department_by_id(parent_id) is None:
            raise NotFoundError("父部门不存在")
        dept = self._repo.create_department(
            name=name, parent_id=parent_id, leader_id=leader_id, sort_order=sort_order
        )
        return self._department_to_dict(dept)

    def update_department(
        self,
        department_id: str,
        *,
        name: str | None = None,
        parent_id: str | None = None,
        leader_id: str | None = None,
        sort_order: int | None = None,
    ) -> dict:
        if self._repo.get_department_by_id(department_id) is None:
            raise NotFoundError("部门不存在")
        if parent_id is not None:
            if parent_id == department_id:
                raise BadRequestError("部门不能将自身设为父部门")
            if self._repo.get_department_by_id(parent_id) is None:
                raise NotFoundError("父部门不存在")
        dept = self._repo.update_department(
            department_id,
            name=name,
            parent_id=parent_id,
            leader_id=leader_id,
            sort_order=sort_order,
        )
        return self._department_to_dict(dept)

    def delete_department(self, department_id: str) -> None:
        if self._repo.get_department_by_id(department_id) is None:
            raise NotFoundError("部门不存在")
        if not self._repo.delete_department(department_id):
            raise ConflictError("存在子部门，无法删除")

    # ------------------------------------------------------------------ #
    # Users
    # ------------------------------------------------------------------ #
    def list_users(
        self,
        *,
        keyword: str | None = None,
        department_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        users, total = self._repo.list_users(
            keyword=keyword, department_id=department_id, page=page, page_size=page_size
        )
        items = [self._user_to_dict(u, self._role_codes(u.id)) for u in users]
        return {"items": items, "total": total}

    def create_user(
        self,
        *,
        username: str,
        password: str,
        display_name: str,
        department_id: str | None = None,
        role_ids: list[str] | None = None,
        status: int = 1,
    ) -> dict:
        if self._repo.find_user_by_username(username) is not None:
            raise ConflictError("用户名已存在")
        if department_id is not None and self._repo.get_department_by_id(department_id) is None:
            raise NotFoundError("部门不存在")

        user = self._repo.create_user(
            username=username,
            password_hash=self._hash_password(password),
            display_name=display_name,
            department_id=department_id,
            status=status,
            role_ids=role_ids or [],
        )
        return self._load_user(user.id)

    def update_user(
        self,
        user_id: str,
        *,
        password: str | None = None,
        display_name: str | None = None,
        department_id: str | None = None,
        status: int | None = None,
        role_ids: list[str] | None = None,
    ) -> dict:
        if self._repo.get_user_by_id(user_id) is None:
            raise NotFoundError("用户不存在")
        if department_id is not None and self._repo.get_department_by_id(department_id) is None:
            raise NotFoundError("部门不存在")

        self._repo.update_user(
            user_id,
            password_hash=self._hash_password(password) if password else None,
            display_name=display_name,
            department_id=department_id,
            status=status,
            role_ids=role_ids,
        )
        return self._load_user(user_id)

    def delete_user(self, user_id: str) -> None:
        if not self._repo.delete_user(user_id):
            raise NotFoundError("用户不存在")

    # ------------------------------------------------------------------ #
    # Roles
    # ------------------------------------------------------------------ #
    def list_roles(self) -> list[dict]:
        roles = self._repo.list_roles()
        return [
            {
                "id": role.id,
                "role_name": role.role_name,
                "role_code": role.role_code,
                "description": role.description,
                "permissions": [
                    {"permission_code": p.permission_code, "permission_type": p.permission_type}
                    for p in self._repo.get_role_permissions(role.id)
                ],
            }
            for role in roles
        ]

    def create_role(
        self, *, role_name: str, role_code: str, description: str | None = None
    ) -> dict:
        if self._repo.get_role_by_code(role_code) is not None:
            raise ConflictError("角色编码已存在")
        role = self._repo.create_role(
            role_name=role_name, role_code=role_code, description=description
        )
        return {
            "id": role.id,
            "role_name": role.role_name,
            "role_code": role.role_code,
            "description": role.description,
            "permissions": [],
        }

    def replace_role_permissions(
        self, role_id: str, permissions: list[tuple[str, str]]
    ) -> None:
        if self._repo.get_role_by_id(role_id) is None:
            raise NotFoundError("角色不存在")
        self._repo.replace_role_permissions(role_id, permissions)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _hash_password(self, password: str) -> str:
        try:
            return self._password_hasher.hash(password)
        except ValueError as exc:
            raise BadRequestError("密码长度超过 bcrypt 72 字节上限", detail=str(exc)) from exc

    def _role_codes(self, user_id: str) -> list[str]:
        return [role.role_code for role in self._repo.get_user_roles(user_id)]

    def _load_user(self, user_id: str) -> dict:
        user = self._repo.get_user_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        return self._user_to_dict(user, self._role_codes(user_id))

    def _user_to_dict(self, user, role_codes: list[str]) -> dict:
        department = user.department
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "department_id": user.department_id,
            "department_name": department.name if department is not None else None,
            "status": user.status,
            "roles": role_codes,
        }

    def _department_to_dict(self, dept) -> dict:
        return {
            "id": dept.id,
            "parent_id": dept.parent_id,
            "name": dept.name,
            "leader_id": dept.leader_id,
            "sort_order": dept.sort_order,
        }
