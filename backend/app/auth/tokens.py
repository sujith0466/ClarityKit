from datetime import UTC, datetime, timedelta
from typing import Any

import jwt


class AuthTokenError(Exception):
    """Base exception for authentication token errors."""

    pass


class TokenExpiredError(AuthTokenError):
    """Raised when a token has expired."""

    pass


class TokenInvalidError(AuthTokenError):
    """Raised when a token is invalid or malformed."""

    pass


def generate_token(
    user_id: str,
    email: str,
    secret_key: str,
    expires_in_seconds: int = 3600,
    algorithm: str = "HS256",
) -> str:
    """Generate a signed JWT token containing user identity claims."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_token(
    token: str,
    secret_key: str,
    algorithms: list[str] | None = None,
) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    if not token or not isinstance(token, str):
        raise TokenInvalidError("Token must be a non-empty string.")

    if algorithms is None:
        algorithms = ["HS256"]

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            secret_key,
            algorithms=algorithms,
            options={"require": ["sub", "email", "exp", "iat"]},
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Authentication token has expired.") from e
    except jwt.PyJWTError as e:
        raise TokenInvalidError("Invalid authentication token.") from e
