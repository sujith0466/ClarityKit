"""REST API routes for Lawyer Preparation Briefs."""

import io
import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request, send_file

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.brief.models import (
    BriefNotFoundError,
    DocumentNotFoundError,
    DocumentNotReadyForBriefError,
    InvalidBriefStateError,
)
from app.brief.service import BriefService, get_brief_service

brief_bp = Blueprint("brief", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@brief_bp.route("/documents/<document_id>/brief", methods=["POST"])
@require_auth
def generate_document_brief(document_id: str) -> tuple[Response, int]:
    """Generate or refresh a Lawyer Preparation Brief for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    title = payload.get("title")

    service: BriefService = get_brief_service()
    try:
        brief = service.generate_brief(
            document_id=document_id,
            user_id=current_user.user_id,
            title=title,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "brief": brief.to_dict(),
                }
            ),
            201,
        )
    except DocumentNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Document '{document_id}' was not found.",
                }
            ),
            404,
        )
    except DocumentNotReadyForBriefError as e:
        return (
            jsonify(
                {
                    "error": "conflict",
                    "message": str(e),
                }
            ),
            409,
        )
    except (InvalidBriefStateError, ValueError) as e:
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
        logger.exception(
            "Unexpected error generating brief for document %s: %s", document_id, e
        )
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to generate lawyer preparation brief.",
                }
            ),
            500,
        )


@brief_bp.route("/documents/<document_id>/brief", methods=["GET"])
@require_auth
def get_document_brief(document_id: str) -> tuple[Response, int]:
    """Retrieve existing Lawyer Preparation Brief for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service: BriefService = get_brief_service()
    try:
        brief = service.get_brief_by_document(
            document_id=document_id,
            user_id=current_user.user_id,
        )
        if brief is None:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message": (
                            f"No preparation brief found for document '{document_id}'."
                        ),
                    }
                ),
                404,
            )

        return (
            jsonify(
                {
                    "status": "success",
                    "brief": brief.to_dict(),
                }
            ),
            200,
        )
    except DocumentNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Document '{document_id}' was not found.",
                }
            ),
            404,
        )
    except Exception as e:
        logger.exception(
            "Unexpected error retrieving brief for doc %s: %s", document_id, e
        )
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to retrieve lawyer preparation brief.",
                }
            ),
            500,
        )


@brief_bp.route("/briefs/<brief_id>", methods=["GET"])
@require_auth
def get_brief_by_id(brief_id: str) -> tuple[Response, int]:
    """Retrieve a specific Lawyer Preparation Brief by ID."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service: BriefService = get_brief_service()
    try:
        brief = service.get_brief_by_id(
            brief_id=brief_id,
            user_id=current_user.user_id,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "brief": brief.to_dict(),
                }
            ),
            200,
        )
    except BriefNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Preparation brief '{brief_id}' was not found.",
                }
            ),
            404,
        )
    except Exception as e:
        logger.exception("Unexpected error retrieving brief %s: %s", brief_id, e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to retrieve preparation brief.",
                }
            ),
            500,
        )


@brief_bp.route("/briefs/<brief_id>", methods=["DELETE"])
@require_auth
def delete_brief(brief_id: str) -> tuple[Response, int]:
    """Delete a Lawyer Preparation Brief by ID."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service: BriefService = get_brief_service()
    try:
        deleted = service.delete_brief(
            brief_id=brief_id,
            user_id=current_user.user_id,
        )
        if not deleted:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message": f"Preparation brief '{brief_id}' was not found.",
                    }
                ),
                404,
            )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Preparation brief deleted successfully.",
                }
            ),
            200,
        )
    except BriefNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Preparation brief '{brief_id}' was not found.",
                }
            ),
            404,
        )
    except Exception as e:
        logger.exception("Unexpected error deleting brief %s: %s", brief_id, e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to delete preparation brief.",
                }
            ),
            500,
        )


@brief_bp.route("/briefs/<brief_id>/export/pdf", methods=["GET"])
@require_auth
def export_brief_pdf(brief_id: str) -> Response | tuple[Response, int]:
    """Export Lawyer Preparation Brief as a PDF document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service: BriefService = get_brief_service()
    try:
        pdf_bytes = service.export_brief_pdf(
            brief_id=brief_id,
            user_id=current_user.user_id,
        )
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"lawyer-preparation-brief-{brief_id}.pdf",
        )
    except BriefNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Preparation brief '{brief_id}' was not found.",
                }
            ),
            404,
        )
    except Exception as e:
        logger.exception("Unexpected error exporting brief PDF %s: %s", brief_id, e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to export lawyer preparation brief as PDF.",
                }
            ),
            500,
        )
