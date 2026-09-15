from typing import Any

from flask import Blueprint, Response, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check() -> tuple[Response, int]:
    """Basic health check smoke endpoint."""
    payload: dict[str, Any] = {
        "status": "ok",
        "service": "claritykit-backend",
    }
    return jsonify(payload), 200
