"""T02 测试共享 fixtures。

用内存 SQLite（StaticPool，跨 repository 的按需 session 复用同一连接）装配
轻量组件：IdentityRepository / PasswordHasher / JwtTokenService / AuthService /
OrgService，以及基于 FastAPI TestClient 的 HTTP 应用（依赖覆盖到内存 DB）。

注意：路由（auth/org router）依赖 ``app.api.deps``，会间接 import 整个
composition root（含 T03+ 的 LLM/Milvus/MinIO 等外部集成）。为避免这些重依赖
拖垮纯单元测试，路由相关 import 放在 ``client`` fixture 内部延迟执行。
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.models.entities import Base
from app.infra.config.settings import Settings
from app.infra.persistence.sqlalchemy.identity_repo import SqlIdentityRepository
from app.infra.security.jwt import JwtTokenService
from app.infra.security.password import BcryptPasswordHasher
from app.services.auth_service import AuthService
from app.services.org_service import OrgService


def _install_missing_import_stubs() -> None:
    """为 T02 测试补齐缺失的重型集成 import（不触碰真实服务）。

    ``app.api.deps`` → ``app.factories.infra`` 会顺带 import 整个 composition
    root，其中 ``app/infra/external/embedder/bge_m3.py`` 依赖
    ``pymilvus.model.hybrid.BGEM3EmbeddingFunction``——该子包仅在安装
    ``pymilvus[model]``（内含 torch/transformers，数 GB）时可用。T02 的
    认证/组织路径完全不触及 embedding，这里仅用哑模块占位让模块可 import。
    """
    import importlib.util
    import sys
    import types

    try:
        has_model = importlib.util.find_spec("pymilvus.model") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        has_model = False
    if has_model:
        return

    model = types.ModuleType("pymilvus.model")
    model.__path__ = []  # type: ignore[attr-defined]
    hybrid = types.ModuleType("pymilvus.model.hybrid")
    hybrid.BGEM3EmbeddingFunction = type("BGEM3EmbeddingFunction", (), {})
    sys.modules["pymilvus.model"] = model
    sys.modules["pymilvus.model.hybrid"] = hybrid


_install_missing_import_stubs()

#: 覆盖组织模块所有 RBAC 操作的宽权限集（供 sys_admin 种子角色使用）。
ADMIN_PERMISSIONS: list[tuple[str, str]] = [
    ("org:user", "read"),
    ("org:user", "create"),
    ("org:user", "update"),
    ("org:user", "delete"),
    ("org:role", "read"),
    ("org:role", "create"),
    ("org:role", "update"),
]


@pytest.fixture()
def settings() -> Settings:
    """独立 JWT 配置，避免污染真实 .env 的密钥与过期时间。"""
    return Settings(JWT_SECRET="test-secret-key-0123456789abcdef", JWT_EXPIRE_MINUTES=60)


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def identity_repo(session_factory) -> SqlIdentityRepository:
    return SqlIdentityRepository(session_factory)


@pytest.fixture()
def password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


@pytest.fixture()
def token_service(settings) -> JwtTokenService:
    return JwtTokenService(settings)


@pytest.fixture()
def auth_service(identity_repo, token_service, password_hasher) -> AuthService:
    return AuthService(identity_repo, token_service, password_hasher)


@pytest.fixture()
def org_service(identity_repo, password_hasher) -> OrgService:
    return OrgService(identity_repo, password_hasher)


@pytest.fixture()
def seed_admin(identity_repo, password_hasher) -> dict:
    """播种一个拥有全部组织权限的 sys_admin 用户，返回其登录凭据。"""
    role = identity_repo.create_role("系统管理员", "sys_admin", "全部权限")
    identity_repo.replace_role_permissions(role.id, list(ADMIN_PERMISSIONS))
    identity_repo.create_user(
        "admin", password_hasher.hash("admin123"), "管理员", role_ids=[role.id]
    )
    return {"username": "admin", "password": "admin123", "role_id": role.id}


@pytest.fixture()
def admin_token(seed_admin, auth_service) -> str:
    return auth_service.login(seed_admin["username"], seed_admin["password"]).access_token


@pytest.fixture()
def admin_headers(admin_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def client(auth_service, org_service, identity_repo):
    """返回一个依赖被覆盖到内存 SQLite 的 FastAPI TestClient。"""
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
    from fastapi.testclient import TestClient

    from app.api.auth_router import router as auth_router
    from app.api.deps import get_auth_service, get_identity_repo, get_org_service
    from app.api.org_router import router as org_router
    from app.api.responses import domain_error_handler, validation_error_handler
    from app.domain.exceptions import DomainError

    app = FastAPI()
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(auth_router, prefix="/api")
    app.include_router(org_router, prefix="/api")

    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_org_service] = lambda: org_service
    app.dependency_overrides[get_identity_repo] = lambda: identity_repo

    return TestClient(app)
