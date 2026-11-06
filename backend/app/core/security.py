"""Password hashing (argon2) and session-token helpers. See SECURITY.md §2."""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def new_session_token() -> str:
    """A high-entropy opaque token handed to the client in the cookie."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Only the hash of the token is stored, so a DB read cannot recover live sessions."""
    return hashlib.sha256(token.encode()).hexdigest()
