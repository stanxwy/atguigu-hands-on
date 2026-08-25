"""Authentication security ports (SPEC §9.1 TokenService / PasswordHasher).

These abstractions keep the authentication services decoupled from concrete
security primitives: token issuance/verification (JWT) and password hashing
(bcrypt) are swapped at the composition root (``app/factories/infra.py``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TokenSubject:
    """Minimal subject identifying a user for token issuance.

    Carries exactly the claims required by the JWT contract (SPEC §8):
    ``sub=user_id``, ``username`` and ``roles=[role_code]``.
    """

    user_id: str
    username: str
    roles: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TokenPayload:
    """Decoded token claims returned by :meth:`TokenService.decode`."""

    user_id: str
    username: str
    roles: list[str] = field(default_factory=list)


class TokenError(Exception):
    """Raised when a token cannot be issued or verified."""


class TokenService(ABC):
    """Port for issuing and verifying stateless bearer tokens (SPEC §9.1)."""

    @abstractmethod
    def issue(self, subject: TokenSubject) -> str:
        """Issue a signed token for ``subject``.

        Args:
            subject: User identity to embed in the token.

        Returns:
            An opaque bearer token string.
        """

    @abstractmethod
    def decode(self, token: str) -> TokenPayload:
        """Verify and decode a token.

        Args:
            token: The bearer token string.

        Returns:
            The decoded :class:`TokenPayload`.

        Raises:
            TokenError: If the token is malformed, expired or has a bad
                signature.
        """


class PasswordHasher(ABC):
    """Port for salted password hashing and verification (SPEC §9.1)."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hash a plaintext password with a random salt.

        Args:
            password: Plaintext password.

        Returns:
            The salted hash string (e.g. bcrypt).
        """

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool:
        """Verify a plaintext password against a stored hash.

        Args:
            password: Plaintext password supplied by the caller.
            password_hash: Stored salted hash.

        Returns:
            ``True`` when the password matches, ``False`` otherwise.
        """
