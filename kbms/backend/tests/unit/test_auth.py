"""T02 认证单元测试（SPEC §3.1 / §8 / §9.1）。

覆盖：
1. PasswordHasher（bcrypt hash/verify + 72 字节上限防护）
2. JwtTokenService（issue→decode 往返 / 篡改签名 / 过期）
3. AuthService.login（正确/错误/不存在/禁用用户）
"""

from __future__ import annotations

import pytest

from app.domain.exceptions import ForbiddenError, UnauthorizedError
from app.domain.ports.auth_port import TokenError, TokenSubject
from app.infra.config.settings import Settings
from app.infra.security.jwt import JwtTokenService
from app.infra.security.password import BcryptPasswordHasher


# --------------------------------------------------------------------------- #
# PasswordHasher（bcrypt）
# --------------------------------------------------------------------------- #
def test_bcrypt_hash_and_verify_correct():
    hasher = BcryptPasswordHasher()
    hashed = hasher.hash("s3cret-p@ss")
    assert hashed != "s3cret-p@ss"
    assert hashed.startswith("$2")  # bcrypt 前缀
    assert hasher.verify("s3cret-p@ss", hashed) is True


def test_bcrypt_verify_wrong_password_false():
    hasher = BcryptPasswordHasher()
    hashed = hasher.hash("correct-password")
    assert hasher.verify("wrong-password", hashed) is False


def test_bcrypt_72_byte_limit_raises():
    hasher = BcryptPasswordHasher()
    with pytest.raises(ValueError):
        hasher.hash("a" * 73)  # 73 个 ASCII 字节 > 72


def test_bcrypt_exactly_72_bytes_is_allowed():
    hasher = BcryptPasswordHasher()
    password = "a" * 72
    hashed = hasher.hash(password)
    assert hasher.verify(password, hashed) is True


def test_bcrypt_multibyte_72_byte_boundary():
    # 24 个汉字 = 72 字节（允许）；25 个汉字 = 75 字节（拒绝）。
    hasher = BcryptPasswordHasher()
    hashed = hasher.hash("汉" * 24)
    assert hasher.verify("汉" * 24, hashed) is True
    with pytest.raises(ValueError):
        hasher.hash("汉" * 25)


# --------------------------------------------------------------------------- #
# JwtTokenService（HS256）
# --------------------------------------------------------------------------- #
def test_jwt_issue_decode_roundtrip(token_service):
    token = token_service.issue(
        TokenSubject(user_id="u-1", username="alice", roles=["sys_admin", "viewer"])
    )
    payload = token_service.decode(token)
    assert payload.user_id == "u-1"
    assert payload.username == "alice"
    assert payload.roles == ["sys_admin", "viewer"]


def test_jwt_tampered_signature_raises(token_service):
    token = token_service.issue(TokenSubject(user_id="u-1", username="alice", roles=[]))
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(TokenError):
        token_service.decode(tampered)


def test_jwt_wrong_secret_raises():
    issuer = JwtTokenService(Settings(JWT_SECRET="secret-one-0123456789abcdef", JWT_EXPIRE_MINUTES=60))
    verifier = JwtTokenService(Settings(JWT_SECRET="secret-two-0123456789abcdef", JWT_EXPIRE_MINUTES=60))
    token = issuer.issue(TokenSubject(user_id="u-1", username="alice"))
    with pytest.raises(TokenError):
        verifier.decode(token)


def test_jwt_expired_token_raises():
    # 过期时间设为负值，签发即过期。
    svc = JwtTokenService(Settings(JWT_SECRET="secret-0123456789abcdefghij", JWT_EXPIRE_MINUTES=-1))
    token = svc.issue(TokenSubject(user_id="u-1", username="alice"))
    with pytest.raises(TokenError):
        svc.decode(token)


# --------------------------------------------------------------------------- #
# AuthService.login
# --------------------------------------------------------------------------- #
def _seed_user_with_dept_and_role(identity_repo, password_hasher):
    dept = identity_repo.create_department(name="研发部")
    role = identity_repo.create_role("普通用户", "viewer", "查看")
    identity_repo.replace_role_permissions(
        role.id, [("knowledge:unit", "read"), ("ai", "ai_access")]
    )
    user = identity_repo.create_user(
        username="alice",
        password_hash=password_hasher.hash("alice123"),
        display_name="Alice",
        department_id=dept.id,
        role_ids=[role.id],
    )
    return user, role, dept


def test_login_success_returns_token_user_info_permissions(
    auth_service, identity_repo, password_hasher
):
    _seed_user_with_dept_and_role(identity_repo, password_hasher)

    data = auth_service.login("alice", "alice123")

    assert data.access_token
    assert data.user_info.username == "alice"
    assert data.user_info.display_name == "Alice"
    assert data.user_info.roles == ["viewer"]
    assert data.user_info.department is not None
    assert data.user_info.department.name == "研发部"
    assert {(p.permission_code, p.permission_type) for p in data.permissions} == {
        ("knowledge:unit", "read"),
        ("ai", "ai_access"),
    }


def test_login_wrong_password_raises_unauthorized(auth_service, identity_repo, password_hasher):
    _seed_user_with_dept_and_role(identity_repo, password_hasher)
    with pytest.raises(UnauthorizedError):
        auth_service.login("alice", "wrong-password")


def test_login_unknown_user_raises_unauthorized(auth_service):
    with pytest.raises(UnauthorizedError):
        auth_service.login("ghost", "whatever")


def test_login_disabled_user_raises_forbidden(auth_service, identity_repo, password_hasher):
    identity_repo.create_user("bob", password_hasher.hash("bob123"), "Bob", status=0)
    with pytest.raises(ForbiddenError):
        auth_service.login("bob", "bob123")
