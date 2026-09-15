from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.documents.service import DocumentService
from app.documents.validation import (
    EmptyFileError,
    FileTooLargeError,
    FileValidationError,
    InvalidFileTypeError,
    MissingFileError,
)

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


@documents_bp.route("", methods=["POST"])
@require_auth
def upload_document() -> tuple[Response, int]:
    """Upload and ingest a legal document (PDF)."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    if "file" not in request.files:
        return (
            jsonify(
                {
                    "error": "validation_error",
                    "message": "Multipart form must contain 'file' field.",
                }
            ),
            400,
        )

    uploaded_file = request.files["file"]
    max_size = current_app.config.get("MAX_UPLOAD_SIZE_BYTES", 20 * 1024 * 1024)
    service = DocumentService()

    try:
        doc = service.upload_document(
            user_id=current_user.user_id,
            file_obj=uploaded_file,
            max_size_bytes=max_size,
        )
    except (
        MissingFileError,
        EmptyFileError,
        InvalidFileTypeError,
        FileValidationError,
    ) as e:
        return jsonify({"error": "validation_error", "message": str(e)}), 400
    except FileTooLargeError as e:
        return jsonify({"error": "file_too_large", "message": str(e)}), 413
    except Exception:
        return (
            jsonify(
                {
                    "error": "internal_server_error",
                    "message": "Failed to ingest document.",
                }
            ),
            500,
        )

    payload: dict[str, Any] = {
        "status": "success",
        "document": doc.to_dict(),
    }
    return jsonify(payload), 201


@documents_bp.route("", methods=["GET"])
@require_auth
def list_documents() -> tuple[Response, int]:
    """List all active documents owned by the authenticated user."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = DocumentService()
    docs = service.list_documents(current_user.user_id)

    payload: dict[str, Any] = {
        "status": "success",
        "count": len(docs),
        "documents": [doc.to_dict() for doc in docs],
    }
    return jsonify(payload), 200


@documents_bp.route("/<document_id>", methods=["GET"])
@require_auth
def get_document(document_id: str) -> tuple[Response, int]:
    """Retrieve metadata for a specific document, enforcing strict IDOR protection."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = DocumentService()
    doc = service.get_document(
        user_id=current_user.user_id,
        document_id=document_id,
    )

    # Return 404 for nonexistent OR non-owned document (IDOR protection)
    if doc is None:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "The requested document was not found.",
                }
            ),
            404,
        )

    payload: dict[str, Any] = {
        "status": "success",
        "document": doc.to_dict(),
    }
    return jsonify(payload), 200


@documents_bp.route("/<document_id>", methods=["DELETE"])
@require_auth
def delete_document(document_id: str) -> tuple[Response, int]:
    """Delete a document and clean up storage, enforcing strict IDOR protection."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = DocumentService()
    deleted = service.delete_document(
        user_id=current_user.user_id,
        document_id=document_id,
    )

    # Return 404 for nonexistent OR non-owned document (IDOR protection)
    if not deleted:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "The requested document was not found.",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "status": "success",
                "message": "Document deleted successfully.",
            }
        ),
        200,
    )
