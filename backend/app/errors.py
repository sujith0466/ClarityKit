from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    """Register standard JSON error handlers on the Flask application."""

    @app.errorhandler(400)
    def bad_request(error: HTTPException | Exception) -> tuple[Response, int]:
        payload: dict[str, Any] = {
            "error": "bad_request",
            "message": str(getattr(error, "description", "Bad request.")),
        }
        return jsonify(payload), 400

    @app.errorhandler(404)
    def not_found(error: HTTPException | Exception) -> tuple[Response, int]:
        payload: dict[str, Any] = {
            "error": "not_found",
            "message": "The requested resource was not found.",
        }
        return jsonify(payload), 404

    @app.errorhandler(405)
    def method_not_allowed(error: HTTPException | Exception) -> tuple[Response, int]:
        payload: dict[str, Any] = {
            "error": "method_not_allowed",
            "message": "Method not allowed for the requested resource.",
        }
        return jsonify(payload), 405

    @app.errorhandler(500)
    def internal_server_error(error: HTTPException | Exception) -> tuple[Response, int]:
        payload: dict[str, Any] = {
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
        }
        return jsonify(payload), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> tuple[Response, int]:
        code = error.code if error.code is not None else 500
        payload: dict[str, Any] = {
            "error": error.name.lower().replace(" ", "_"),
            "message": error.description,
        }
        return jsonify(payload), code
