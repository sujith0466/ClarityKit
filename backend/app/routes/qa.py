import logging

from flask import Blueprint, Response, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.qa.models import (
    DocumentNotFoundError,
    DocumentNotReadyForQAError,
    InvalidQuestionError,
    QAError,
    QASessionNotFoundError,
)
from app.qa.service import QAService

logger = logging.getLogger(__name__)

qa_bp = Blueprint("qa", __name__, url_prefix="/api")
qa_service = QAService()


@qa_bp.route("/documents/<document_id>/questions", methods=["POST"])
@require_auth
def ask_question(document_id: str) -> tuple[Response, int]:
    """Ask a question about an owned document and receive a grounded answer."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    data = request.get_json(silent=True) or {}
    question_text = data.get("question")
    session_id = data.get("session_id")

    if not isinstance(question_text, str):
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message": "Question must be a non-empty string.",
                }
            ),
            400,
        )

    try:
        qa_message = qa_service.ask_question(
            document_id=document_id,
            user_id=current_user.user_id,
            question=question_text,
            session_id=session_id,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": qa_message.to_dict(),
                }
            ),
            201,
        )
    except DocumentNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "The requested document was not found.",
                }
            ),
            404,
        )
    except DocumentNotReadyForQAError as e:
        return (
            jsonify(
                {
                    "error": "document_not_ready",
                    "message": str(e),
                }
            ),
            400,
        )
    except (InvalidQuestionError, QASessionNotFoundError) as e:
        return (
            jsonify(
                {
                    "error": "invalid_request",
                    "message": str(e),
                }
            ),
            400,
        )
    except QAError as e:
        logger.error(
            "QA processing error for doc %s: %s", document_id, e, exc_info=True
        )
        return (
            jsonify(
                {
                    "error": "qa_error",
                    "message": "Failed to process question.",
                }
            ),
            500,
        )


@qa_bp.route("/documents/<document_id>/questions", methods=["GET"])
@require_auth
def list_document_questions(document_id: str) -> tuple[Response, int]:
    """List all Q&A messages for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    try:
        messages = qa_service.list_document_messages(
            document_id=document_id, user_id=current_user.user_id
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "messages": [m.to_dict() for m in messages],
                }
            ),
            200,
        )
    except DocumentNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "The requested document was not found.",
                }
            ),
            404,
        )


@qa_bp.route("/documents/<document_id>/qa/sessions", methods=["POST"])
@require_auth
def create_session(document_id: str) -> tuple[Response, int]:
    """Create a new Q&A session for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    data = request.get_json(silent=True) or {}
    title = data.get("title")

    try:
        session = qa_service.create_session(
            document_id=document_id,
            user_id=current_user.user_id,
            title=title,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "session": session.to_dict(),
                }
            ),
            201,
        )
    except DocumentNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "The requested document was not found.",
                }
            ),
            404,
        )


@qa_bp.route("/documents/<document_id>/qa/sessions", methods=["GET"])
@require_auth
def list_sessions(document_id: str) -> tuple[Response, int]:
    """List all Q&A sessions for an owned document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    try:
        sessions = qa_service.list_sessions(
            document_id=document_id, user_id=current_user.user_id
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "sessions": [s.to_dict() for s in sessions],
                }
            ),
            200,
        )
    except DocumentNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "The requested document was not found.",
                }
            ),
            404,
        )


@qa_bp.route("/documents/<document_id>/qa/sessions/<session_id>", methods=["GET"])
@require_auth
def get_session(document_id: str, session_id: str) -> tuple[Response, int]:
    """Retrieve an owned session and its Q&A history."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    try:
        session = qa_service.get_session(
            session_id=session_id, user_id=current_user.user_id
        )
        if session.document_id != document_id:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message": "The requested session was not found.",
                    }
                ),
                404,
            )

        return (
            jsonify(
                {
                    "status": "success",
                    "session": session.to_dict(),
                }
            ),
            200,
        )
    except QASessionNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "The requested session was not found.",
                }
            ),
            404,
        )


@qa_bp.route("/questions/<message_id>", methods=["GET"])
@require_auth
def get_question_message(message_id: str) -> tuple[Response, int]:
    """Retrieve a single Q&A message by ID."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    try:
        message = qa_service.get_message(
            message_id=message_id, user_id=current_user.user_id
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": message.to_dict(),
                }
            ),
            200,
        )
    except QASessionNotFoundError:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": "The requested question was not found.",
                }
            ),
            404,
        )
