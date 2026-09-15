from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import current_app, g, jsonify, request
from werkzeug.exceptions import Unauthorized

from app.auth.models import User
from app.auth.repository import get_user_repository
from app.auth.tokens import TokenExpiredError, TokenInvalidError, decode_token

F = TypeVar("F", bound=Callable[..., Any])


def get_current_user() -> User | None:
    """Retrieve the authenticated user from the current request context."""
    return getattr(g, "current_user", None)


def require_auth(f: F) -> F:
    """Decorator to require a valid Bearer token on protected endpoints."""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": "Authorization header is required.",
                    }
                ),
                401,
            )

        parts = auth_header.strip().split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": (
                            "Invalid Authorization header format. "
                            "Expected 'Bearer <token>'."
                        ),
                    }
                ),
                401,
            )

        token = parts[1]
        secret_key = current_app.config.get("SECRET_KEY", "")

        try:
            payload = decode_token(token, secret_key)
        except TokenExpiredError:
            return (
                jsonify(
                    {
                        "error": "token_expired",
                        "message": "Authentication token has expired.",
                    }
                ),
                401,
            )
        except (TokenInvalidError, Unauthorized):
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": "Invalid or malformed authentication token.",
                    }
                ),
                401,
            )

        user_id = payload.get("sub")
        if not user_id:
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": "Token subject claim is missing.",
                    }
                ),
                401,
            )

        repository = get_user_repository()
        user = repository.get_by_id(user_id)
        if user is None or not user.is_active:
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": (
                            "User associated with token is not active "
                            "or no longer exists."
                        ),
                    }
                ),
                401,
            )

        # Store authenticated user in request context
        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function  # type: ignore[return-value]


def require_ownership(
    loader_func: Callable[[str], Any | None],
    id_param_name: str = "resource_id",
) -> Callable[[F], F]:
    """Decorator to enforce strict resource ownership and IDOR protection.

    Rules:
    - Unauthenticated -> 401
    - Nonexistent resource -> 404
    - Resource owned by another user -> 404 (IDOR protection)
    - Owned resource -> allowed
    """

    def decorator(f: F) -> F:
        @wraps(f)
        @require_auth
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            current_user: User | None = get_current_user()
            if current_user is None:
                return (
                    jsonify(
                        {
                            "error": "unauthorized",
                            "message": "Authentication required.",
                        }
                    ),
                    401,
                )

            resource_id = kwargs.get(id_param_name)
            if not resource_id:
                return (
                    jsonify(
                        {
                            "error": "bad_request",
                            "message": f"Missing required parameter '{id_param_name}'.",
                        }
                    ),
                    400,
                )

            resource = loader_func(str(resource_id))
            # IDOR Protection: Return 404 if resource does not exist
            # or belongs to another user
            if resource is None:
                return (
                    jsonify(
                        {
                            "error": "not_found",
                            "message": "The requested resource was not found.",
                        }
                    ),
                    404,
                )

            resource_owner_id = getattr(resource, "user_id", None) or getattr(
                resource, "owner_id", None
            )
            if resource_owner_id != current_user.user_id:
                return (
                    jsonify(
                        {
                            "error": "not_found",
                            "message": "The requested resource was not found.",
                        }
                    ),
                    404,
                )

            # Store verified resource in request context
            g.current_resource = resource
            return f(*args, **kwargs)

        return decorated_function  # type: ignore[return-value]

    return decorator
