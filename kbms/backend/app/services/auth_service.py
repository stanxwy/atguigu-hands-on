"""Authentication application service (SPEC §9.1 AuthService)."""

from __future__ import annotations

from app.domain.exceptions import ForbiddenError, UnauthorizedError
from app.domain.ports.auth_port import PasswordHasher, TokenError, TokenService, TokenSubject
from app.domain.ports.identity_repository import IdentityRepository
from app.schema.auth_schema import DepartmentInfo, LoginData, PermissionItem, UserInfo


class AuthService:
    """Login / token verification orchestration."""

    def __init__(
        self,
        identity_repo: IdentityRepository,
        token_service: TokenService,
        password_hasher: PasswordHasher,
    ) -> None:
        self._identity_repo = identity_repo
        self._token_service = token_service
        self._password_hasher = password_hasher

    def login(self, username: str, password: str) -> LoginData:
        """Authenticate a user and issue a token (SPEC §3.1 ``POST /auth/login``).

        Args:
            username: Unique login name.
            password: Plaintext password.

        Returns:
            ``LoginData`` with ``access_token``, ``user_info`` and a flat
            ``permissions`` list.

        Raises:
            UnauthorizedError: Bad credentials (same message for unknown user
                and wrong password, to avoid user enumeration).
            ForbiddenError: The user account is disabled.
        """
        user = self._identity_repo.find_user_by_username(username)
        if user is None or not self._password_hasher.verify(password, user.password_hash):
            raise UnauthorizedError("用户名或密码错误")
        if user.status != 1:
            raise ForbiddenError("用户已被禁用，请联系管理员")

        # Re-fetch by id so the ``department`` relationship is preloaded (the
        # find_user_by_username query does not eager-load it).
        user = self._identity_repo.get_user_by_id(user.id)
        if user is None:
            raise UnauthorizedError("用户不存在")

        role_codes, permissions = self._resolve_roles_and_permissions(user.id)
        token = self._token_service.issue(
            TokenSubject(user_id=user.id, username=user.username, roles=role_codes)
        )
        return LoginData(
            access_token=token,
            user_info=self._build_user_info(user, role_codes),
            permissions=permissions,
        )

    def get_current_user_by_token(self, token: str) -> dict:
        """Resolve the current user from a bearer token (SPEC §3.1 ``GET /me``).

        Re-reads the user + roles + permissions from the DB (not just the JWT
        claims) so that disabled accounts and permission changes take effect
        immediately.

        Returns:
            Dict with keys ``id``, ``username``, ``display_name``,
            ``department``, ``roles`` and ``permissions``.

        Raises:
            UnauthorizedError: Invalid/expired token or unknown user.
            ForbiddenError: The user account is disabled.
        """
        try:
            payload = self._token_service.decode(token)
        except TokenError as exc:
            raise UnauthorizedError("无效或过期的令牌", detail=str(exc)) from exc

        user = self._identity_repo.get_user_by_id(payload.user_id)
        if user is None:
            raise UnauthorizedError("用户不存在")
        if user.status != 1:
            raise ForbiddenError("用户已被禁用，请联系管理员")

        role_codes, permissions = self._resolve_roles_and_permissions(user.id)
        info = self._build_user_info(user, role_codes).model_dump()
        info["permissions"] = [p.model_dump() for p in permissions]
        return info

    def _resolve_roles_and_permissions(
        self, user_id: str
    ) -> tuple[list[str], list[PermissionItem]]:
        roles = self._identity_repo.get_user_roles(user_id)
        role_codes = [role.role_code for role in roles]
        return role_codes, self._collect_permissions(roles)

    def _collect_permissions(self, roles) -> list[PermissionItem]:
        """Flatten role permissions, deduplicated by ``(code, type)``."""
        seen: set[tuple[str, str]] = set()
        items: list[PermissionItem] = []
        for role in roles:
            for perm in self._identity_repo.get_role_permissions(role.id):
                key = (perm.permission_code, perm.permission_type)
                if key not in seen:
                    seen.add(key)
                    items.append(
                        PermissionItem(
                            permission_code=perm.permission_code,
                            permission_type=perm.permission_type,
                        )
                    )
        return items

    def _build_user_info(self, user, role_codes: list[str]) -> UserInfo:
        department = user.department
        return UserInfo(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            department=(
                DepartmentInfo(id=department.id, name=department.name)
                if department is not None
                else None
            ),
            roles=role_codes,
        )
