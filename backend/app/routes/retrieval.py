import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.documents.service import DocumentService
from app.retrieval.indexing_service import default_indexing_service
from app.retrieval.models import (
    IndexingError,
    InvalidQueryError,
    RetrievalError,
)
from app.retrieval.retrieval_service import default_retrieval_service

retrieval_bp = Blueprint("retrieval", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@retrieval_bp.route("/documents/<document_id>/index", methods=["POST"])
@require_auth
def trigger_indexing(document_id: str) -> tuple[Response, int]:
    """Trigger chunking, embeddings, and vector indexing for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    doc_service = DocumentService()
    doc = doc_service.get_document(
        user_id=current_user.user_id,
        document_id=document_id,
    )
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

    try:
        chunks = default_indexing_service.index_document(
            user_id=current_user.user_id, document_id=document_id
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "document_id": document_id,
                    "chunk_count": len(chunks),
                    "chunks": [c.to_dict() for c in chunks],
                }
            ),
            200,
        )
    except IndexingError as e:
        logger.warning(f"Indexing failed for doc {document_id}: {e}")
        return (
            jsonify(
                {
                    "error": "indexing_failed",
                    "message": str(e),
                }
            ),
            422,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during indexing of doc {document_id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "An unexpected error occurred during document indexing.",
                }
            ),
            500,
        )


@retrieval_bp.route("/documents/<document_id>/chunks", methods=["GET"])
@require_auth
def get_document_chunks(document_id: str) -> tuple[Response, int]:
    """Retrieve all indexed chunks for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    doc_service = DocumentService()
    doc = doc_service.get_document(
        user_id=current_user.user_id,
        document_id=document_id,
    )
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

    chunks = default_indexing_service.get_document_chunks(
        user_id=current_user.user_id, document_id=document_id
    )
    if chunks is None:
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
                "document_id": document_id,
                "count": len(chunks),
                "chunks": [c.to_dict() for c in chunks],
            }
        ),
        200,
    )


@retrieval_bp.route("/documents/<document_id>/index", methods=["GET"])
@require_auth
def get_indexing_summary(document_id: str) -> tuple[Response, int]:
    """Retrieve indexing summary and statistics for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    doc_service = DocumentService()
    doc = doc_service.get_document(
        user_id=current_user.user_id,
        document_id=document_id,
    )
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

    summary = default_indexing_service.get_indexing_summary(
        user_id=current_user.user_id, document_id=document_id
    )
    if summary is None:
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
                "indexing": summary,
            }
        ),
        200,
    )


@retrieval_bp.route("/retrieval/search", methods=["POST"])
@require_auth
def search_chunks() -> tuple[Response, int]:
    """Execute vector semantic retrieval strictly over the caller's documents."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    query = payload.get("query", "")
    document_id = payload.get("document_id")
    top_k = payload.get("top_k")
    min_similarity = payload.get("min_similarity")

    # If document_id is provided, verify caller ownership
    if document_id:
        doc_service = DocumentService()
        doc = doc_service.get_document(
            user_id=current_user.user_id,
            document_id=document_id,
        )
        if doc is None:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message": f"Document '{document_id}' not found.",
                    }
                ),
                404,
            )

    try:
        results = default_retrieval_service.retrieve(
            user_id=current_user.user_id,
            query=query,
            document_id=document_id,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        return (
            jsonify(
                {
                    "status": "success",
                    "query": query,
                    "count": len(results),
                    "results": [r.to_dict() for r in results],
                }
            ),
            200,
        )
    except InvalidQueryError as e:
        return (
            jsonify(
                {
                    "error": "invalid_query",
                    "message": str(e),
                }
            ),
            400,
        )
    except RetrievalError as e:
        logger.error(
            f"Retrieval error for user {current_user.user_id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "error": "retrieval_failed",
                    "message": str(e),
                }
            ),
            500,
        )
    except Exception as e:
        logger.error(f"Unexpected error during retrieval: {e}", exc_info=True)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "An unexpected error occurred during retrieval.",
                }
            ),
            500,
        )
