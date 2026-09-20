import logging

from flask import Blueprint, Response, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.trust.models import (
    DocumentNotFoundError,
    DocumentNotReadyForTrustError,
    InvalidTrustInputError,
    TrustError,
)
from app.trust.service import TrustService

trust_bp = Blueprint("trust", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@trust_bp.route("/documents/<document_id>/trust", methods=["GET"])
@require_auth
def get_document_trust(document_id: str) -> tuple[Response, int]:
    """Retrieve full Trust & Safety report for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = TrustService()
    try:
        report = service.get_document_trust_report(
            document_id=document_id,
            user_id=current_user.user_id,
        )
        return (
            jsonify({"status": "success", "trust_report": report.to_dict()}),
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
    except DocumentNotReadyForTrustError as e:
        return (
            jsonify(
                {
                    "error": "not_ready",
                    "message": str(e),
                }
            ),
            422,
        )
    except TrustError as e:
        logger.error("Trust assessment error on doc %s: %s", document_id, e)
        return (
            jsonify({"error": "trust_error", "message": str(e)}),
            500,
        )


@trust_bp.route("/documents/<document_id>/trust/assess", methods=["POST"])
@require_auth
def assess_claims(document_id: str) -> tuple[Response, int]:
    """Evaluate bounded ad-hoc claims against trust and safety rules."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return (
            jsonify({"error": "bad_request", "message": "JSON body is required."}),
            400,
        )

    claims_input = body.get("claims")
    if not isinstance(claims_input, list):
        return (
            jsonify(
                {"error": "bad_request", "message": "'claims' field must be a list."}
            ),
            400,
        )

    service = TrustService()
    try:
        assessed = service.assess_ad_hoc_claims(
            document_id=document_id,
            user_id=current_user.user_id,
            claims_input=claims_input,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "document_id": document_id,
                    "assessed_claims": [ac.to_dict() for ac in assessed],
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
    except InvalidTrustInputError as e:
        return (
            jsonify({"error": "invalid_input", "message": str(e)}),
            400,
        )
    except TrustError as e:
        logger.error("Trust ad-hoc assessment error on doc %s: %s", document_id, e)
        return (
            jsonify({"error": "trust_error", "message": str(e)}),
            500,
        )
