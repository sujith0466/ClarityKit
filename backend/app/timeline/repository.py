"""Repository layer for Timeline persistence and tenant isolation (Phase 14)."""

import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

from psycopg2.extensions import connection

from app.database import get_db_connection
from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.timeline.models import DocumentTimeline

logger = logging.getLogger(__name__)


class TimelineRepository(ABC):
    """Abstract repository interface for Timeline persistence."""

    @abstractmethod
    def save_timeline(
        self, timeline: DocumentTimeline, user_id: str
    ) -> DocumentTimeline:
        """Persist a document timeline record."""

    @abstractmethod
    def get_timeline_by_id(
        self, timeline_id: str, user_id: str
    ) -> DocumentTimeline | None:
        """Retrieve a timeline by ID for an authorized user."""

    @abstractmethod
    def get_timeline_by_document_id(
        self, document_id: str, user_id: str
    ) -> DocumentTimeline | None:
        """Retrieve an existing timeline for a specific document."""

    @abstractmethod
    def list_timelines_for_user(self, user_id: str) -> list[DocumentTimeline]:
        """List all timelines belonging to a user."""

    @abstractmethod
    def delete_timeline(self, timeline_id: str, user_id: str) -> bool:
        """Delete a timeline record."""

    @abstractmethod
    def delete_timelines_for_document(self, document_id: str, user_id: str) -> int:
        """Cascade delete all timelines associated with a specific document."""


class InMemoryTimelineRepository(TimelineRepository):
    """Thread-safe in-memory repository for Timelines."""

    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._timelines: dict[str, DocumentTimeline] = {}
        self._lock = threading.Lock()
        self._doc_repo = document_repository or in_memory_document_repository

    def clear(self) -> None:
        with self._lock:
            self._timelines.clear()

    def _verify_document_ownership(self, document_id: str, user_id: str) -> bool:
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return False
        return True

    def save_timeline(
        self, timeline: DocumentTimeline, user_id: str
    ) -> DocumentTimeline:
        with self._lock:
            if timeline.user_id != user_id:
                raise ValueError("Unauthorized timeline user ownership mismatch.")
            if not self._verify_document_ownership(timeline.document_id, user_id):
                raise ValueError("Unauthorized document ownership in timeline.")
            self._timelines[timeline.id] = timeline
            return timeline

    def get_timeline_by_id(
        self, timeline_id: str, user_id: str
    ) -> DocumentTimeline | None:
        with self._lock:
            tl = self._timelines.get(timeline_id)
            if not tl or tl.user_id != user_id:
                return None
            if not self._verify_document_ownership(tl.document_id, user_id):
                return None
            return tl

    def get_timeline_by_document_id(
        self, document_id: str, user_id: str
    ) -> DocumentTimeline | None:
        with self._lock:
            if not self._verify_document_ownership(document_id, user_id):
                return None
            for tl in self._timelines.values():
                if tl.document_id == document_id and tl.user_id == user_id:
                    return tl
            return None

    def list_timelines_for_user(self, user_id: str) -> list[DocumentTimeline]:
        with self._lock:
            results = [
                tl
                for tl in self._timelines.values()
                if tl.user_id == user_id
                and self._verify_document_ownership(tl.document_id, user_id)
            ]
            results.sort(key=lambda t: t.created_at, reverse=True)
            return results

    def delete_timeline(self, timeline_id: str, user_id: str) -> bool:
        with self._lock:
            tl = self._timelines.get(timeline_id)
            if not tl or tl.user_id != user_id:
                return False
            del self._timelines[timeline_id]
            return True

    def delete_timelines_for_document(self, document_id: str, user_id: str) -> int:
        with self._lock:
            to_delete = [
                tid
                for tid, tl in self._timelines.items()
                if tl.user_id == user_id and tl.document_id == document_id
            ]
            for tid in to_delete:
                del self._timelines[tid]
            return len(to_delete)


class PostgresTimelineRepository(TimelineRepository):
    """PostgreSQL repository for Document Timeline persistence."""

    def __init__(
        self,
        db_connection_factory: Any = get_db_connection,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self._get_connection = db_connection_factory
        self._doc_repo = document_repository or in_memory_document_repository

    def _verify_document_ownership(self, document_id: str, user_id: str) -> bool:
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return False
        return True

    def save_timeline(
        self, timeline: DocumentTimeline, user_id: str
    ) -> DocumentTimeline:
        if timeline.user_id != user_id:
            raise ValueError("Unauthorized timeline user ownership mismatch.")
        if not self._verify_document_ownership(timeline.document_id, user_id):
            raise ValueError("Unauthorized document ownership in timeline.")

        tl_dict = timeline.to_dict()
        tl_payload = {
            "items": tl_dict["items"],
            "summary": tl_dict["summary"],
        }

        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO document_timelines
                        (id, user_id, document_id, title, timeline_data,
                         created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        timeline_data = EXCLUDED.timeline_data,
                        updated_at = EXCLUDED.updated_at;
                    """,
                    (
                        timeline.id,
                        timeline.user_id,
                        timeline.document_id,
                        timeline.title,
                        json.dumps(tl_payload),
                        timeline.created_at,
                        timeline.updated_at,
                    ),
                )
            conn.commit()
            return timeline
        finally:
            conn.close()

    def get_timeline_by_id(
        self, timeline_id: str, user_id: str
    ) -> DocumentTimeline | None:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, document_id, title,
                           timeline_data, created_at, updated_at
                    FROM document_timelines
                    WHERE id = %s AND user_id = %s;
                    """,
                    (timeline_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None

                doc_id = str(row[2])
                if not self._verify_document_ownership(doc_id, user_id):
                    return None

                tl_data = row[4] if isinstance(row[4], dict) else json.loads(row[4])
                data = {
                    "id": str(row[0]),
                    "user_id": str(row[1]),
                    "document_id": doc_id,
                    "title": row[3],
                    "document_title": tl_data.get("document_title", ""),
                    "items": tl_data.get("items", []),
                    "summary": tl_data.get("summary", {}),
                    "created_at": row[5],
                    "updated_at": row[6],
                }
                return DocumentTimeline.from_dict(data)
        finally:
            conn.close()

    def get_timeline_by_document_id(
        self, document_id: str, user_id: str
    ) -> DocumentTimeline | None:
        if not self._verify_document_ownership(document_id, user_id):
            return None

        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, document_id, title,
                           timeline_data, created_at, updated_at
                    FROM document_timelines
                    WHERE document_id = %s AND user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT 1;
                    """,
                    (document_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None

                tl_data = row[4] if isinstance(row[4], dict) else json.loads(row[4])
                data = {
                    "id": str(row[0]),
                    "user_id": str(row[1]),
                    "document_id": str(row[2]),
                    "title": row[3],
                    "document_title": tl_data.get("document_title", ""),
                    "items": tl_data.get("items", []),
                    "summary": tl_data.get("summary", {}),
                    "created_at": row[5],
                    "updated_at": row[6],
                }
                return DocumentTimeline.from_dict(data)
        finally:
            conn.close()

    def list_timelines_for_user(self, user_id: str) -> list[DocumentTimeline]:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, document_id, title,
                           timeline_data, created_at, updated_at
                    FROM document_timelines
                    WHERE user_id = %s
                    ORDER BY created_at DESC;
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
                results: list[DocumentTimeline] = []
                for row in rows:
                    doc_id = str(row[2])
                    if not self._verify_document_ownership(doc_id, user_id):
                        continue
                    tl_data = row[4] if isinstance(row[4], dict) else json.loads(row[4])
                    data = {
                        "id": str(row[0]),
                        "user_id": str(row[1]),
                        "document_id": doc_id,
                        "title": row[3],
                        "document_title": tl_data.get("document_title", ""),
                        "items": tl_data.get("items", []),
                        "summary": tl_data.get("summary", {}),
                        "created_at": row[5],
                        "updated_at": row[6],
                    }
                    results.append(DocumentTimeline.from_dict(data))
                return results
        finally:
            conn.close()

    def delete_timeline(self, timeline_id: str, user_id: str) -> bool:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_timelines
                    WHERE id = %s AND user_id = %s;
                    """,
                    (timeline_id, user_id),
                )
                deleted = bool(cur.rowcount > 0)
            conn.commit()
            return deleted
        finally:
            conn.close()

    def delete_timelines_for_document(self, document_id: str, user_id: str) -> int:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_timelines
                    WHERE user_id = %s AND document_id = %s;
                    """,
                    (user_id, document_id),
                )
                deleted_count = int(cur.rowcount)
            conn.commit()
            return deleted_count
        finally:
            conn.close()


in_memory_timeline_repository = InMemoryTimelineRepository()
