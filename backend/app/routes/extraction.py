import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.extraction.models import (
    DocumentNotFoundError,
    DocumentNotReadyForExtractionError,
    ExtractionError,
    InvalidExtractionSchemaError,
)
from app.extraction.service import ExtractionService

extraction_bp = Blueprint("extraction", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@extraction_bp.route("/documents/<document_id>/extract", methods=["POST"])
@require_auth
def extract_document_understanding(document_id: str) -> tuple[Response, int]:
    """Trigger structured legal fact extraction for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    metadata = payload.get("metadata", {})

    service = ExtractionService()
    try:
        understanding = service.extract_document(
            document_id=document_id,
            user_id=current_user.user_id,
            metadata=metadata,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "understanding": understanding.to_dict(),
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
    except DocumentNotReadyForExtractionError as e:
        logger.warning(
            "Document %s not ready for extraction: %s",
            document_id,
            e,
        )
        return (
            jsonify(
                {
                    "error": "not_ready",
                    "message": str(e),
                }
            ),
            422,
        )
    except InvalidExtractionSchemaError as e:
        logger.error(
            "Schema validation failed for extraction on doc %s: %s",
            document_id,
            e,
        )
        return (
            jsonify(
                {
                    "error": "invalid_schema",
                    "message": str(e),
                }
            ),
            422,
        )
    except ExtractionError as e:
        logger.error(
            "Extraction error for doc %s: %s",
            document_id,
            e,
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "error": "extraction_failed",
                    "message": str(e),
                }
            ),
            500,
        )
    except Exception as e:
        logger.error(
            "Unexpected error during extraction for doc %s: %s",
            document_id,
            e,
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "An unexpected error occurred during extraction.",
                }
            ),
            500,
        )


@extraction_bp.route("/documents/<document_id>/understanding", methods=["GET"])
@require_auth
def get_document_understanding(document_id: str) -> tuple[Response, int]:
    """Retrieve structured extraction facts and review flags for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = ExtractionService()
    try:
        understanding = service.get_document_understanding(
            document_id=document_id,
            user_id=current_user.user_id,
        )
        if understanding is None:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message": (
                            "No structured extraction found for document "
                            f"'{document_id}'."
                        ),
                    }
                ),
                404,
            )

        return (
            jsonify(
                {
                    "status": "success",
                    "understanding": understanding.to_dict(),
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
        logger.error(
            "Unexpected error fetching understanding for doc %s: %s",
            document_id,
            e,
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": (
                        "An unexpected error occurred retrieving document "
                        "understanding."
                    ),
                }
            ),
            500,
        )
