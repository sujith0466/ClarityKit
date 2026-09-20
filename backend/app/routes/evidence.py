import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.evidence.models import (
    DocumentNotFoundError,
    DocumentNotReadyForEvidenceError,
    EvidenceError,
    InvalidEvidenceInputError,
)
from app.evidence.service import EvidenceService

evidence_bp = Blueprint("evidence", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@evidence_bp.route("/documents/<document_id>/evidence", methods=["GET"])
@require_auth
def get_document_evidence(document_id: str) -> tuple[Response, int]:
    """Retrieve mechanical evidence verification report for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = EvidenceService()
    try:
        report = service.get_document_evidence(
            document_id=document_id,
            user_id=current_user.user_id,
        )
        return jsonify({"status": "success", "evidence_report": report.to_dict()}), 200
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
    except DocumentNotReadyForEvidenceError as e:
        return (
            jsonify(
                {
                    "error": "not_ready",
                    "message": str(e),
                }
            ),
            422,
        )
    except EvidenceError as e:
        logger.error("Evidence generation error on doc %s: %s", document_id, e)
        return (
            jsonify(
                {
                    "error": "evidence_error",
                    "message": "Failed to generate evidence report.",
                }
            ),
            500,
        )


@evidence_bp.route("/documents/<document_id>/evidence/validate", methods=["POST"])
@require_auth
def validate_ad_hoc_evidence(document_id: str) -> tuple[Response, int]:
    """Validate ad-hoc claim payloads against owned document text."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    raw_claims = payload.get("claims", [])

    service = EvidenceService()
    try:
        report = service.validate_ad_hoc_claims(
            document_id=document_id,
            user_id=current_user.user_id,
            raw_claims=raw_claims,
        )
        return jsonify({"status": "success", "evidence_report": report.to_dict()}), 200
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
    except DocumentNotReadyForEvidenceError as e:
        return (
            jsonify(
                {
                    "error": "not_ready",
                    "message": str(e),
                }
            ),
            422,
        )
    except InvalidEvidenceInputError as e:
        return (
            jsonify(
                {
                    "error": "invalid_input",
                    "message": str(e),
                }
            ),
            400,
        )
    except EvidenceError as e:
        logger.error("Ad-hoc evidence validation error on doc %s: %s", document_id, e)
        return (
            jsonify(
                {
                    "error": "evidence_error",
                    "message": "Failed to validate claims.",
                }
            ),
            500,
        )
