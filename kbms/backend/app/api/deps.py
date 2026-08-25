"""FastAPI dependency providers for the new KBMS services (SPEC §5.1)."""

from __future__ import annotations

from app.domain.ports.identity_repository import IdentityRepository
from app.factories import infra as infra_factories
from app.factories.services import create_auth_service, create_org_service
from app.services.auth_service import AuthService
from app.services.org_service import OrgService


def get_auth_service() -> AuthService:
    """Return the cached :class:`AuthService` singleton."""
    return create_auth_service()


def get_org_service() -> OrgService:
    """Return the cached :class:`OrgService` singleton."""
    return create_org_service()


def get_identity_repo() -> IdentityRepository:
    """Return the cached :class:`IdentityRepository` adapter."""
    return infra_factories.get_identity_repo()
