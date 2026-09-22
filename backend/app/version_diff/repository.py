"""Repository layer for Version Diff persistence and tenant isolation (Phase 14)."""

import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

from psycopg2.extensions import connection

from app.database import get_db_connection
from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.version_diff.models import DocumentVersionDiff

logger = logging.getLogger(__name__)


class VersionDiffRepository(ABC):
    """Abstract repository interface for Version Diff persistence."""

    @abstractmethod
    def save_version_diff(
        self, version_diff: DocumentVersionDiff, user_id: str
    ) -> DocumentVersionDiff:
        """Persist a version diff record."""

    @abstractmethod
    def get_version_diff_by_id(
        self, diff_id: str, user_id: str
    ) -> DocumentVersionDiff | None:
        """Retrieve a version diff by ID for an authorized user."""

    @abstractmethod
    def list_version_diffs_for_user(self, user_id: str) -> list[DocumentVersionDiff]:
        """List all version diffs belonging to a user."""

    @abstractmethod
    def delete_version_diff(self, diff_id: str, user_id: str) -> bool:
        """Delete a version diff record."""

    @abstractmethod
    def delete_diffs_for_document(self, document_id: str, user_id: str) -> int:
        """Cascade delete all version diffs containing the specified document ID."""


class InMemoryVersionDiffRepository(VersionDiffRepository):
    """Thread-safe in-memory repository for Version Diffs (testing & fallback)."""

    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._diffs: dict[str, DocumentVersionDiff] = {}
        self._lock = threading.Lock()
        self._doc_repo = document_repository or in_memory_document_repository

    def clear(self) -> None:
        with self._lock:
            self._diffs.clear()

    def _verify_documents_ownership(self, v1_id: str, v2_id: str, user_id: str) -> bool:
        for doc_id in (v1_id, v2_id):
            doc = self._doc_repo.get_by_id(doc_id)
            if (
                doc is None
                or doc.user_id != user_id
                or doc.status == DocumentStatus.DELETED
            ):
                return False
        return True

    def save_version_diff(
        self, version_diff: DocumentVersionDiff, user_id: str
    ) -> DocumentVersionDiff:
        with self._lock:
            if version_diff.user_id != user_id:
                raise ValueError("Unauthorized version diff user ownership mismatch.")
            if not self._verify_documents_ownership(
                version_diff.v1_document.id, version_diff.v2_document.id, user_id
            ):
                raise ValueError("Unauthorized document ownership in version diff.")
            self._diffs[version_diff.id] = version_diff
            return version_diff

    def get_version_diff_by_id(
        self, diff_id: str, user_id: str
    ) -> DocumentVersionDiff | None:
        with self._lock:
            diff = self._diffs.get(diff_id)
            if not diff or diff.user_id != user_id:
                return None
            if not self._verify_documents_ownership(
                diff.v1_document.id, diff.v2_document.id, user_id
            ):
                return None
            return diff

    def list_version_diffs_for_user(self, user_id: str) -> list[DocumentVersionDiff]:
        with self._lock:
            results = [
                d
                for d in self._diffs.values()
                if d.user_id == user_id
                and self._verify_documents_ownership(
                    d.v1_document.id, d.v2_document.id, user_id
                )
            ]
            results.sort(key=lambda d: d.created_at, reverse=True)
            return results

    def delete_version_diff(self, diff_id: str, user_id: str) -> bool:
        with self._lock:
            diff = self._diffs.get(diff_id)
            if not diff or diff.user_id != user_id:
                return False
            del self._diffs[diff_id]
            return True

    def delete_diffs_for_document(self, document_id: str, user_id: str) -> int:
        with self._lock:
            to_delete = [
                did
                for did, diff in self._diffs.items()
                if diff.user_id == user_id
                and (
                    diff.v1_document.id == document_id
                    or diff.v2_document.id == document_id
                )
            ]
            for did in to_delete:
                del self._diffs[did]
            return len(to_delete)


class PostgresVersionDiffRepository(VersionDiffRepository):
    """PostgreSQL repository for Document Version Diff persistence."""

    def __init__(
        self,
        db_connection_factory: Any = get_db_connection,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self._get_connection = db_connection_factory
        self._doc_repo = document_repository or in_memory_document_repository

    def _verify_documents_ownership(self, v1_id: str, v2_id: str, user_id: str) -> bool:
        for doc_id in (v1_id, v2_id):
            doc = self._doc_repo.get_by_id(doc_id)
            if (
                doc is None
                or doc.user_id != user_id
                or doc.status == DocumentStatus.DELETED
            ):
                return False
        return True

    def save_version_diff(
        self, version_diff: DocumentVersionDiff, user_id: str
    ) -> DocumentVersionDiff:
        if version_diff.user_id != user_id:
            raise ValueError("Unauthorized version diff user ownership mismatch.")
        if not self._verify_documents_ownership(
            version_diff.v1_document.id, version_diff.v2_document.id, user_id
        ):
            raise ValueError("Unauthorized document ownership in version diff.")

        diff_dict = version_diff.to_dict()
        diff_payload = {
            "v1_document": diff_dict["v1_document"],
            "v2_document": diff_dict["v2_document"],
            "findings": diff_dict["findings"],
            "summary": diff_dict["summary"],
        }

        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO document_version_diffs
                        (id, user_id, v1_document_id, v2_document_id,
                         title, diff_data, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        diff_data = EXCLUDED.diff_data,
                        updated_at = EXCLUDED.updated_at;
                    """,
                    (
                        version_diff.id,
                        version_diff.user_id,
                        version_diff.v1_document.id,
                        version_diff.v2_document.id,
                        version_diff.title,
                        json.dumps(diff_payload),
                        version_diff.created_at,
                        version_diff.updated_at,
                    ),
                )
            conn.commit()
            return version_diff
        finally:
            conn.close()

    def get_version_diff_by_id(
        self, diff_id: str, user_id: str
    ) -> DocumentVersionDiff | None:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, v1_document_id, v2_document_id, title,
                           diff_data, created_at, updated_at
                    FROM document_version_diffs
                    WHERE id = %s AND user_id = %s;
                    """,
                    (diff_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None

                v1_id = str(row[2])
                v2_id = str(row[3])
                if not self._verify_documents_ownership(v1_id, v2_id, user_id):
                    return None

                diff_data = row[5] if isinstance(row[5], dict) else json.loads(row[5])
                data = {
                    "id": str(row[0]),
                    "user_id": str(row[1]),
                    "title": row[4],
                    "v1_document": diff_data.get(
                        "v1_document",
                        {"id": v1_id, "filename": "", "version_label": "v1"},
                    ),
                    "v2_document": diff_data.get(
                        "v2_document",
                        {"id": v2_id, "filename": "", "version_label": "v2"},
                    ),
                    "findings": diff_data.get("findings", []),
                    "summary": diff_data.get("summary", {}),
                    "created_at": row[6],
                    "updated_at": row[7],
                }
                return DocumentVersionDiff.from_dict(data)
        finally:
            conn.close()

    def list_version_diffs_for_user(self, user_id: str) -> list[DocumentVersionDiff]:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, v1_document_id, v2_document_id, title,
                           diff_data, created_at, updated_at
                    FROM document_version_diffs
                    WHERE user_id = %s
                    ORDER BY created_at DESC;
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
                results: list[DocumentVersionDiff] = []
                for row in rows:
                    v1_id = str(row[2])
                    v2_id = str(row[3])
                    if not self._verify_documents_ownership(v1_id, v2_id, user_id):
                        continue
                    diff_data = (
                        row[5] if isinstance(row[5], dict) else json.loads(row[5])
                    )
                    data = {
                        "id": str(row[0]),
                        "user_id": str(row[1]),
                        "title": row[4],
                        "v1_document": diff_data.get(
                            "v1_document",
                            {"id": v1_id, "filename": "", "version_label": "v1"},
                        ),
                        "v2_document": diff_data.get(
                            "v2_document",
                            {"id": v2_id, "filename": "", "version_label": "v2"},
                        ),
                        "findings": diff_data.get("findings", []),
                        "summary": diff_data.get("summary", {}),
                        "created_at": row[6],
                        "updated_at": row[7],
                    }
                    results.append(DocumentVersionDiff.from_dict(data))
                return results
        finally:
            conn.close()

    def delete_version_diff(self, diff_id: str, user_id: str) -> bool:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_version_diffs
                    WHERE id = %s AND user_id = %s;
                    """,
                    (diff_id, user_id),
                )
                deleted = bool(cur.rowcount > 0)
            conn.commit()
            return deleted
        finally:
            conn.close()

    def delete_diffs_for_document(self, document_id: str, user_id: str) -> int:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_version_diffs
                    WHERE user_id = %s AND (v1_document_id = %s OR v2_document_id = %s);
                    """,
                    (user_id, document_id, document_id),
                )
                deleted_count = int(cur.rowcount)
            conn.commit()
            return deleted_count
        finally:
            conn.close()


in_memory_version_diff_repository = InMemoryVersionDiffRepository()
