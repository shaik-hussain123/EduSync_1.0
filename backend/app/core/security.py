"""
app/core/security.py

Password hashing, verification, and JWT utilities for EduSync ERP.

Functions:
  - hash_password()         : Hashes a plain-text password with bcrypt.
  - verify_password()       : Verifies a plain-text password against a hash.
  - create_access_token()   : Creates a signed JWT access token.
  - decode_access_token()   : Decodes and validates a JWT access token.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings


def hash_password(plain_password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.

    Args:
        plain_password: The raw password provided by the user.

    Returns:
        A bcrypt-hashed string safe to store in the database.
    """
    pw_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.

    Args:
        plain_password:  The raw password from a login attempt.
        hashed_password: The bcrypt hash stored in MongoDB.

    Returns:
        True if the password matches, False otherwise.
    """
    try:
        pw_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pw_bytes, hashed_bytes)
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# JWT Access Token
# ──────────────────────────────────────────────────────────────────────────────
def create_access_token(payload: dict[str, Any]) -> str:
    """
    Creates a signed JWT access token.

    The token embeds the provided payload and adds:
      - iat  (issued at)
      - exp  (expiry, from settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    Args:
        payload: A dict containing the claims to embed in the token.
                 Expected keys: student_id, email, role, usn.

    Returns:
        A signed JWT string ready to be returned to the client.
    """
    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims = {
        **payload,
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT access token.

    Args:
        token: The raw JWT string received from the client.

    Returns:
        The decoded payload dict if the token is valid and not expired.

    Raises:
        JWTError: If the token is invalid, tampered, or expired.
                  Callers should catch this and return HTTP 401.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
