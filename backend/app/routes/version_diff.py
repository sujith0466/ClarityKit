"""REST API routes for Document Version Diff (Phase 14)."""

import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.version_diff.models import (
    DocumentNotReadyForVersionDiffError,
    InvalidVersionDiffInputError,
    VersionDiffNotFoundError,
)
from app.version_diff.service import VersionDiffService

version_diff_bp = Blueprint("version_diff", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


def get_version_diff_service() -> VersionDiffService:
    """Factory creating VersionDiffService with active repositories."""
    return VersionDiffService()


@version_diff_bp.route("/version-diffs", methods=["POST"])
@require_auth
def create_version_diff() -> tuple[Response, int]:
    """Generate and persist a version diff between Version 1 (Base) and
    Version 2 (Revised).
    """
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    v1_document_id = str(payload.get("v1_document_id") or "")
    v2_document_id = str(payload.get("v2_document_id") or "")
    title = payload.get("title")

    service = get_version_diff_service()
    try:
        diff = service.generate_version_diff(
            v1_document_id=v1_document_id,
            v2_document_id=v2_document_id,
            user_id=current_user.user_id,
            title=title,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "version_diff": diff.to_dict(),
                }
            ),
            201,
        )
    except VersionDiffNotFoundError as e:
        return (
            jsonify({"error": "not_found", "message": str(e)}),
            404,
        )
    except DocumentNotReadyForVersionDiffError as e:
        return (
            jsonify({"error": "conflict", "message": str(e)}),
            409,
        )
    except InvalidVersionDiffInputError as e:
        return (
            jsonify({"error": "bad_request", "message": str(e)}),
            400,
        )
    except Exception as e:
        logger.exception("Unexpected error generating version diff: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to generate document version diff.",
                }
            ),
            500,
        )


@version_diff_bp.route("/version-diffs", methods=["GET"])
@require_auth
def list_version_diffs() -> tuple[Response, int]:
    """List all version diffs belonging to the authenticated user."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = get_version_diff_service()
    try:
        diffs = service.list_version_diffs_for_user(current_user.user_id)
        return (
            jsonify(
                {
                    "status": "success",
                    "count": len(diffs),
                    "version_diffs": [d.to_dict() for d in diffs],
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Unexpected error listing version diffs: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to list version diffs.",
                }
            ),
            500,
        )


@version_diff_bp.route("/version-diffs/<diff_id>", methods=["GET"])
@require_auth
def get_version_diff(diff_id: str) -> tuple[Response, int]:
    """Retrieve a specific version diff by ID."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = get_version_diff_service()
    try:
        diff = service.get_version_diff_by_id(diff_id, current_user.user_id)
        return (
            jsonify(
                {
                    "status": "success",
                    "version_diff": diff.to_dict(),
                }
            ),
            200,
        )
    except VersionDiffNotFoundError as e:
        return (
            jsonify({"error": "not_found", "message": str(e)}),
            404,
        )
    except Exception as e:
        logger.exception("Unexpected error retrieving version diff: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to retrieve version diff.",
                }
            ),
            500,
        )


@version_diff_bp.route("/version-diffs/<diff_id>", methods=["DELETE"])
@require_auth
def delete_version_diff(diff_id: str) -> tuple[Response, int]:
    """Delete a version diff record."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = get_version_diff_service()
    try:
        deleted = service.delete_version_diff(diff_id, current_user.user_id)
        if not deleted:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message": f"Version diff '{diff_id}' not found.",
                    }
                ),
                404,
            )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Version diff deleted successfully.",
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Unexpected error deleting version diff: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to delete version diff.",
                }
            ),
            500,
        )
