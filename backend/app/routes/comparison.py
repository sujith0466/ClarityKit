"""REST API routes for Multi-Document Comparison & Consistency Analysis (Phase 13)."""

import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.comparison.models import (
    ComparisonNotFoundError,
    DocumentNotReadyForComparisonError,
    InvalidComparisonInputError,
)
from app.comparison.service import ComparisonService, get_comparison_service

comparison_bp = Blueprint("comparison", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@comparison_bp.route("/comparisons", methods=["POST"])
@require_auth
def create_comparison() -> tuple[Response, int]:
    """Create a new multi-document comparison for 2–5 owned documents."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    document_ids = payload.get("document_ids", [])
    title = payload.get("title")

    service: ComparisonService = get_comparison_service()
    try:
        comparison = service.generate_comparison(
            document_ids=document_ids,
            user_id=current_user.user_id,
            title=title,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "comparison": comparison.to_dict(),
                }
            ),
            201,
        )
    except ComparisonNotFoundError as e:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": str(e),
                }
            ),
            404,
        )
    except DocumentNotReadyForComparisonError as e:
        return (
            jsonify(
                {
                    "error": "conflict",
                    "message": str(e),
                }
            ),
            409,
        )
    except InvalidComparisonInputError as e:
        return (
            jsonify(
                {
                    "error": "bad_request",
                    "message": str(e),
                }
            ),
            400,
        )
    except Exception as e:
        logger.exception("Unexpected error generating comparison: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to generate multi-document comparison.",
                }
            ),
            500,
        )


@comparison_bp.route("/comparisons", methods=["GET"])
@require_auth
def list_comparisons() -> tuple[Response, int]:
    """List all comparisons for the authenticated user."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service: ComparisonService = get_comparison_service()
    try:
        comparisons = service.list_comparisons_for_user(user_id=current_user.user_id)
        return (
            jsonify(
                {
                    "status": "success",
                    "comparisons": [c.to_dict() for c in comparisons],
                    "total": len(comparisons),
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Unexpected error listing comparisons: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to list comparisons.",
                }
            ),
            500,
        )


@comparison_bp.route("/comparisons/<comparison_id>", methods=["GET"])
@require_auth
def get_comparison(comparison_id: str) -> tuple[Response, int]:
    """Retrieve a specific comparison by ID enforcing tenant isolation."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service: ComparisonService = get_comparison_service()
    try:
        comparison = service.get_comparison_by_id(
            comparison_id=comparison_id,
            user_id=current_user.user_id,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "comparison": comparison.to_dict(),
                }
            ),
            200,
        )
    except ComparisonNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Comparison '{comparison_id}' was not found.",
                }
            ),
            404,
        )
    except Exception as e:
        logger.exception(
            "Unexpected error retrieving comparison %s: %s", comparison_id, e
        )
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to retrieve comparison.",
                }
            ),
            500,
        )


@comparison_bp.route("/comparisons/<comparison_id>", methods=["DELETE"])
@require_auth
def delete_comparison(comparison_id: str) -> tuple[Response, int]:
    """Delete a comparison by ID enforcing tenant isolation."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service: ComparisonService = get_comparison_service()
    try:
        deleted = service.delete_comparison(
            comparison_id=comparison_id,
            user_id=current_user.user_id,
        )
        if not deleted:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message": f"Comparison '{comparison_id}' was not found.",
                    }
                ),
                404,
            )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Comparison deleted successfully.",
                }
            ),
            200,
        )
    except ComparisonNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Comparison '{comparison_id}' was not found.",
                }
            ),
            404,
        )
    except Exception as e:
        logger.exception(
            "Unexpected error deleting comparison %s: %s", comparison_id, e
        )
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to delete comparison.",
                }
            ),
            500,
        )
