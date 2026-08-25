"""bcrypt implementation of the PasswordHasher port (SPEC §8 salted hashing)."""

from __future__ import annotations

import bcrypt

from app.domain.ports.auth_port import PasswordHasher

#: bcrypt operates on the first 72 bytes of input; bcrypt>=4.1 raises
#: ``ValueError`` for longer passwords. Enforced here so callers fail loudly
#: instead of silently producing a truncated/incorrect hash.
_BCRYPT_MAX_BYTES: int = 72


class BcryptPasswordHasher(PasswordHasher):
    """bcrypt salted password hasher."""

    def hash(self, password: str) -> str:
        """Hash ``password`` with a random per-call salt.

        Args:
            password: Plaintext password.

        Returns:
            The bcrypt hash string.

        Raises:
            ValueError: If the password exceeds bcrypt's 72-byte limit.
        """
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > _BCRYPT_MAX_BYTES:
            raise ValueError("密码长度超过 bcrypt 72 字节上限")
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    def verify(self, password: str, password_hash: str) -> bool:
        """Verify ``password`` against ``password_hash`` (never raises)."""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False
