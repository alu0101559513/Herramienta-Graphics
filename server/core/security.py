from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash
from server.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Description:
        Hash a plain-text password using the configured password hasher.

    Args:
        password (str):
            Plain-text password.

    Returns:
        str:
            Password hash safe to store in the database.
    """

    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Description:
        Verify a plain-text password against a stored password hash.

    Args:
        password (str):
            Plain-text password.

        hashed_password (str):
            Stored password hash.

    Returns:
        bool:
            True when the password matches the hash, otherwise False.
    """

    return password_hash.verify(password, hashed_password)


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Description:
        Create a signed JWT access token.

        The token includes subject, issued-at, not-before and expiration claims.

    Args:
        subject (str | Any):
            Token subject. In this application it is usually the user id.

        expires_delta (timedelta | None):
            Optional custom expiration duration. When omitted, the configured
            JWT_EXPIRE_HOURS value is used.

    Returns:
        str:
            Encoded JWT access token.
    """

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=settings.JWT_EXPIRE_HOURS))

    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "nbf": now,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Description:
        Decode and validate a JWT access token.

        Expired, malformed or invalid tokens return None instead of raising.

    Args:
        token (str):
            JWT access token.

    Returns:
        dict[str, Any] | None:
            Token payload when valid, otherwise None.
    """

    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
