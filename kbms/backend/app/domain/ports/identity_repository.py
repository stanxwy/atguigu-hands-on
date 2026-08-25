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
