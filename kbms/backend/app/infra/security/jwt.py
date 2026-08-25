"""PyJWT (HS256) implementation of the TokenService port (SPEC §8)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.domain.ports.auth_port import TokenError, TokenPayload, TokenService, TokenSubject
from app.infra.config.settings import Settings


class JwtTokenService(TokenService):
    """Stateless JWT token service (HS256, payload ``{sub, username, roles}``)."""

    ALGORITHM: str = "HS256"

    def __init__(self, settings: Settings) -> None:
        self._secret: str = settings.JWT_SECRET
        self._expire_minutes: int = settings.JWT_EXPIRE_MINUTES

    def issue(self, subject: TokenSubject) -> str:
        """Issue a signed JWT for ``subject``.

        Claims follow SPEC §8: ``sub=user_id``, ``username``, ``roles``;
        ``exp`` is ``now + JWT_EXPIRE_MINUTES``.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject.user_id,
            "username": subject.username,
            "roles": subject.roles,
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self.ALGORITHM)

    def decode(self, token: str) -> TokenPayload:
        """Verify and decode a JWT; raises :class:`TokenError` on any failure."""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self.ALGORITHM])
        except jwt.PyJWTError as exc:
            raise TokenError(str(exc)) from exc

        return TokenPayload(
            user_id=payload.get("sub", ""),
            username=payload.get("username", ""),
            roles=payload.get("roles") or [],
        )
