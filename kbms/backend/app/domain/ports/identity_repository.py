"""Identity & organization repository port (SPEC §9.1 IdentityRepository)."""

from abc import ABC, abstractmethod
from typing import Any

from app.domain.models.entities import Department, Role, RolePermission, User


class IdentityRepository(ABC):
    """Persistence port for users / departments / roles / user_roles / role_permissions.

    Implementations own the transaction boundary; returned ORM entities are
    detached but expose their loaded column attributes (``id``, ``username``,
    ``role_code``, ``permission_code``, ...) for read access by services.
    """

    @abstractmethod
    def find_user_by_username(self, username: str) -> User | None:
        """Look up a user by unique ``username``.

        Args:
            username: Unique login name.

        Returns:
            The matching ``User`` or ``None`` if not found.
        """

    @abstractmethod
    def get_user_roles(self, user_id: str) -> list[Role]:
        """Return all roles assigned to a user.

        Args:
            user_id: Target user id.

        Returns:
            List of ``Role`` (possibly empty).
        """

    @abstractmethod
    def get_role_permissions(self, role_id: str) -> list[RolePermission]:
        """Return all ``(permission_code, permission_type)`` rows for a role.

        Args:
            role_id: Target role id.

        Returns:
            List of ``RolePermission`` (possibly empty).
        """

    @abstractmethod
    def list_departments_tree(self) -> list[dict[str, Any]]:
        """Return the full department tree.

        Returns:
            Nested list of department dicts: ``{id, parent_id, name,
            leader_id, sort_order, children[]}`` (root nodes first, children
            recursively attached). Matches ``GET /api/org/departments``.
        """

    @abstractmethod
    def create_user(
        self,
        username: str,
        password_hash: str,
        display_name: str,
        department_id: str | None = None,
        status: int = 1,
        role_ids: list[str] | None = None,
    ) -> User:
        """Create a user and (optionally) bind roles atomically.

        Args:
            username: Unique login name.
            password_hash: bcrypt hash of the password.
            display_name: Display name.
            department_id: Optional department FK.
            status: 1 enabled / 0 disabled.
            role_ids: Optional role ids to assign (creates user_roles rows).

        Returns:
            The persisted ``User``.
        """

    @abstractmethod
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
        """Update user fields; ``None`` means "leave unchanged".

        When ``role_ids`` is provided (not ``None``), the user's role bindings
        are fully replaced (delete + insert in one transaction).

        Args:
            user_id: Target user id.
            password_hash: New bcrypt hash, if changing password.
            display_name: New display name.
            department_id: New department FK.
            status: New status.
            role_ids: New full role id list (replacement semantics).

        Returns:
            Updated ``User`` or ``None`` if not found.
        """

    @abstractmethod
    def create_role(
        self, role_name: str, role_code: str, description: str | None = None
    ) -> Role:
        """Create a role.

        Args:
            role_name: Human-readable role name.
            role_code: Unique role code (e.g. ``sys_admin``).
            description: Optional description.

        Returns:
            The persisted ``Role``.
        """

    @abstractmethod
    def replace_role_permissions(
        self, role_id: str, permissions: list[tuple[str, str]]
    ) -> None:
        """Replace a role's permissions atomically (SPEC §3.1 transaction覆盖).

        Args:
            role_id: Target role id.
            permissions: Full list of ``(permission_code, permission_type)``.
        """

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> User | None:
        """Fetch a user by id with its ``department`` relationship preloaded.

        Args:
            user_id: Target user id.

        Returns:
            The matching ``User`` (``department`` eagerly loaded) or ``None``.
        """

    @abstractmethod
    def list_users(
        self,
        *,
        keyword: str | None = None,
        department_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        """Paginated user list with optional keyword / department filters.

        Args:
            keyword: Case-insensitive partial match on ``username`` or
                ``display_name``.
            department_id: Exact department filter.
            page: 1-based page number.
            page_size: Page size.

        Returns:
            ``(items, total)`` ordered by ``created_at`` descending; each item
            has its ``department`` relationship preloaded.
        """

    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """Delete a user by id.

        Args:
            user_id: Target user id.

        Returns:
            ``True`` when a user was deleted, ``False`` when not found.
        """

    @abstractmethod
    def list_roles(self) -> list[Role]:
        """Return all roles ordered by ``created_at`` ascending."""

    @abstractmethod
    def get_role_by_id(self, role_id: str) -> Role | None:
        """Fetch a role by id (or ``None``)."""

    @abstractmethod
    def get_role_by_code(self, role_code: str) -> Role | None:
        """Fetch a role by unique ``role_code`` (or ``None``)."""

    @abstractmethod
    def list_departments(self) -> list[Department]:
        """Return the flat department list ordered by ``sort_order``."""

    @abstractmethod
    def get_department_by_id(self, department_id: str) -> Department | None:
        """Fetch a department by id (or ``None``)."""

    @abstractmethod
    def create_department(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        leader_id: str | None = None,
        sort_order: int = 0,
    ) -> Department:
        """Create a department.

        Args:
            name: Department name.
            parent_id: Optional parent department id (root when ``None``).
            leader_id: Optional leader user id.
            sort_order: Display order.

        Returns:
            The persisted ``Department``.
        """

    @abstractmethod
    def update_department(
        self,
        department_id: str,
        *,
        name: str | None = None,
        parent_id: str | None = None,
        leader_id: str | None = None,
        sort_order: int | None = None,
    ) -> Department | None:
        """Update department fields; ``None`` means "leave unchanged".

        Returns:
            Updated ``Department`` or ``None`` if not found.
        """

    @abstractmethod
    def delete_department(self, department_id: str) -> bool:
        """Delete a department.

        Args:
            department_id: Target department id.

        Returns:
            ``False`` when the department does not exist or still has children
            (avoiding orphaned subtrees / FK violations); ``True`` on success.
        """
