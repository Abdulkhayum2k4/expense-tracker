from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import settings

# PasswordHash.recommended() uses Argon2id
password_hash = PasswordHash.recommended()

# Used so a login with an unknown email takes as long as one with a wrong password
_DUMMY_HASH = password_hash.hash("dummy-password-for-timing")

AUTH_COOKIE = "access_token"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if hashed is None:
        password_hash.verify(password, _DUMMY_HASH)
        return False
    return password_hash.verify(password, hashed)


@dataclass(frozen=True)
class TokenClaims:
    user_id: str
    version: int


def create_access_token(user_id: str, version: int = 0) -> str:
    """`version` is the user's token_version; bumping it revokes every older token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "ver": version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenClaims | None:
    """Return the token's claims, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError:
        return None
    sub, ver = payload.get("sub"), payload.get("ver", 0)
    if not isinstance(sub, str) or not isinstance(ver, int):
        return None
    return TokenClaims(sub, ver)
