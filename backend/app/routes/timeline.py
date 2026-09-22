"""REST API routes for Deadline & Obligation Timeline (Phase 14)."""

import logging
from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.auth.context import get_current_user, require_auth
from app.auth.models import User
from app.timeline.models import (
    DocumentNotReadyForTimelineError,
    InvalidTimelineInputError,
    TimelineNotFoundError,
)
from app.timeline.service import TimelineService

timeline_bp = Blueprint("timeline", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


def get_timeline_service() -> TimelineService:
    """Factory creating TimelineService with active repositories."""
    return TimelineService()


@timeline_bp.route("/documents/<document_id>/timeline", methods=["POST"])
@require_auth
def create_document_timeline(document_id: str) -> tuple[Response, int]:
    """Generate and persist a chronological timeline for a specific document."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    title = payload.get("title")

    service = get_timeline_service()
    try:
        timeline = service.generate_document_timeline(
            document_id=document_id,
            user_id=current_user.user_id,
            title=title,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "timeline": timeline.to_dict(),
                }
            ),
            201,
        )
    except TimelineNotFoundError as e:
        return (
            jsonify({"error": "not_found", "message": str(e)}),
            404,
        )
    except DocumentNotReadyForTimelineError as e:
        return (
            jsonify({"error": "conflict", "message": str(e)}),
            409,
        )
    except InvalidTimelineInputError as e:
        return (
            jsonify({"error": "bad_request", "message": str(e)}),
            400,
        )
    except Exception as e:
        logger.exception("Unexpected error generating timeline: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to generate document timeline.",
                }
            ),
            500,
        )


@timeline_bp.route("/documents/<document_id>/timeline", methods=["GET"])
@require_auth
def get_document_timeline(document_id: str) -> tuple[Response, int]:
    """Retrieve an existing persisted timeline for a document (side-effect free)."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = get_timeline_service()
    try:
        timeline = service.get_timeline_by_document_id(
            document_id=document_id,
            user_id=current_user.user_id,
        )
        return (
            jsonify(
                {
                    "status": "success",
                    "timeline": timeline.to_dict(),
                }
            ),
            200,
        )
    except TimelineNotFoundError as e:
        return (
            jsonify({"error": "not_found", "message": str(e)}),
            404,
        )
    except Exception as e:
        logger.exception("Unexpected error retrieving document timeline: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to retrieve document timeline.",
                }
            ),
            500,
        )


@timeline_bp.route("/timelines", methods=["GET"])
@require_auth
def list_timelines() -> tuple[Response, int]:
    """List all timelines belonging to the authenticated user."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = get_timeline_service()
    try:
        timelines = service.list_timelines_for_user(current_user.user_id)
        return (
            jsonify(
                {
                    "status": "success",
                    "count": len(timelines),
                    "timelines": [t.to_dict() for t in timelines],
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Unexpected error listing timelines: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to list timelines.",
                }
            ),
            500,
        )


@timeline_bp.route("/timelines/<timeline_id>", methods=["GET"])
@require_auth
def get_timeline(timeline_id: str) -> tuple[Response, int]:
    """Retrieve a specific timeline by timeline ID."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = get_timeline_service()
    try:
        timeline = service.get_timeline_by_id(timeline_id, current_user.user_id)
        return (
            jsonify(
                {
                    "status": "success",
                    "timeline": timeline.to_dict(),
                }
            ),
            200,
        )
    except TimelineNotFoundError as e:
        return (
            jsonify({"error": "not_found", "message": str(e)}),
            404,
        )
    except Exception as e:
        logger.exception("Unexpected error retrieving timeline: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to retrieve timeline.",
                }
            ),
            500,
        )


@timeline_bp.route("/timelines/<timeline_id>", methods=["DELETE"])
@require_auth
def delete_timeline(timeline_id: str) -> tuple[Response, int]:
    """Delete a timeline record."""
    current_user: User | None = get_current_user()
    if current_user is None:
        return (
            jsonify({"error": "unauthorized", "message": "Authentication required."}),
            401,
        )

    service = get_timeline_service()
    try:
        deleted = service.delete_timeline(timeline_id, current_user.user_id)
        if not deleted:
            return (
                jsonify(
                    {
                        "error": "not_found",
                        "message": f"Timeline '{timeline_id}' not found.",
                    }
                ),
                404,
            )
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Timeline deleted successfully.",
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Unexpected error deleting timeline: %s", e)
        return (
            jsonify(
                {
                    "error": "internal_error",
                    "message": "Failed to delete timeline.",
                }
            ),
            500,
        )
