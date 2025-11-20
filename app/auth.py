"""
Authentication and authorization helpers for the ImageModify backend.

This module handles password hashing, JWT token creation and
verification. It relies on the python-jose and passlib libraries. In
a production system you might extend this module to support
refresh tokens or additional authentication strategies.
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

import bcrypt
import hashlib 

from .config import settings


def _normalize_password_for_bcrypt(password: str) -> bytes:
    """Return a byte string suitable for bcrypt.

    bcrypt has a 72-byte input limit. To avoid issues with long
    passwords, we pre-hash inputs longer than 72 bytes with SHA-256
    (this mirrors the behavior of bcrypt-based schemes that salt a
    digest). Using a fixed-length digest keeps verification simple.
    """
    b = password.encode("utf-8")
    if len(b) > 72:
        return hashlib.sha256(b).digest()
    return b


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt and return UTF-8 string."""
    pw = _normalize_password_for_bcrypt(password)
    hashed = bcrypt.hashpw(pw, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed version."""
    pw = _normalize_password_for_bcrypt(plain_password)
    # hashed_password may be a str from DB; ensure bytes for checkpw
    return bcrypt.checkpw(pw, hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token with an optional expiration delta."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or settings.access_token_expires)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode a JWT token and return the payload on success or None on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None