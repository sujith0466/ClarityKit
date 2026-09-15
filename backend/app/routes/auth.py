from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.service import (
    AuthService,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserInactiveError,
    ValidationError,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register() -> tuple[Response, int]:
    """Register a new user account."""
    if not request.is_json:
        return (
            jsonify(
                {
                    "error": "bad_request",
                    "message": "Request body must be valid JSON.",
                }
            ),
            400,
        )

    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not email or not password or not name:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "Email, password, and name are required.",
                }
            ),
            400,
        )

    secret_key = current_app.config.get("SECRET_KEY", "")
    token_expires_in = current_app.config.get("JWT_EXPIRATION_SECONDS", 3600)
    service = AuthService()

    try:
        user, token = service.register(
            email=str(email),
            password=str(password),
            name=str(name),
            secret_key=secret_key,
            token_expires_in=token_expires_in,
        )
    except ValidationError as e:
        return jsonify({"error": "validation_error", "message": str(e)}), 400
    except UserAlreadyExistsError as e:
        return jsonify({"error": "conflict", "message": str(e)}), 409

    payload: dict[str, Any] = {
        "status": "success",
        "user": user.to_dict(),
        "token": token,
    }
    return jsonify(payload), 201


@auth_bp.route("/login", methods=["POST"])
def login() -> tuple[Response, int]:
    """Authenticate an existing user."""
    if not request.is_json:
        return (
            jsonify(
                {
                    "error": "bad_request",
                    "message": "Request body must be valid JSON.",
                }
            ),
            400,
        )

    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "Email and password are required.",
                }
            ),
            400,
        )

    secret_key = current_app.config.get("SECRET_KEY", "")
    token_expires_in = current_app.config.get("JWT_EXPIRATION_SECONDS", 3600)
    service = AuthService()

    try:
        user, token = service.login(
            email=str(email),
            password=str(password),
            secret_key=secret_key,
            token_expires_in=token_expires_in,
        )
    except (InvalidCredentialsError, UserInactiveError) as e:
        return jsonify({"error": "unauthorized", "message": str(e)}), 401

    payload: dict[str, Any] = {
        "status": "success",
        "user": user.to_dict(),
        "token": token,
    }
    return jsonify(payload), 200


@auth_bp.route("/logout", methods=["POST"])
def logout() -> tuple[Response, int]:
    """Logout endpoint acknowledging client session termination."""
    return (
        jsonify(
            {
                "status": "success",
                "message": "Logged out successfully.",
            }
        ),
        200,
    )


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me() -> tuple[Response, int]:
    """Retrieve authenticated user details."""
    current_user = get_current_user()
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

    payload: dict[str, Any] = {
        "status": "success",
        "user": current_user.to_dict(),
    }
    return jsonify(payload), 200
