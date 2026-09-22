"""Repository layer for Multi-Document Comparison persistence (Phase 13)."""

import json
import logging
from abc import ABC, abstractmethod
from threading import Lock
from typing import Any

from psycopg2.extensions import connection

from app.comparison.models import DocumentComparison
from app.database import get_db_connection
from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository

logger = logging.getLogger(__name__)


class ComparisonRepository(ABC):
    """Abstract repository for Document Comparison persistence."""

    @abstractmethod
    def save_comparison(
        self, comparison: DocumentComparison, user_id: str
    ) -> DocumentComparison:
        """Persist or update a document comparison."""
        pass

    @abstractmethod
    def get_comparison_by_id(
        self, comparison_id: str, user_id: str
    ) -> DocumentComparison | None:
        """Retrieve a comparison by ID enforcing tenant isolation."""
        pass

    @abstractmethod
    def list_comparisons_for_user(self, user_id: str) -> list[DocumentComparison]:
        """List all comparisons for a specific user ordered by created_at descending."""
        pass

    @abstractmethod
    def delete_comparison(self, comparison_id: str, user_id: str) -> bool:
        """Delete a comparison by ID enforcing tenant isolation."""
        pass

    @abstractmethod
    def delete_comparisons_for_document(self, document_id: str, user_id: str) -> int:
        """Delete all comparisons referencing a specific deleted document."""
        pass


class InMemoryComparisonRepository(ComparisonRepository):
    """Thread-safe in-memory repository for comparisons."""

    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._lock = Lock()
        self._doc_repo = document_repository or in_memory_document_repository
        # Key: comparison_id -> DocumentComparison
        self._comparisons: dict[str, DocumentComparison] = {}

    def clear(self) -> None:
        with self._lock:
            self._comparisons.clear()

    def _verify_documents_ownership(
        self, document_ids: list[str], user_id: str
    ) -> bool:
        for doc_id in document_ids:
            doc = self._doc_repo.get_by_id(doc_id)
            if (
                doc is None
                or doc.user_id != user_id
                or doc.status == DocumentStatus.DELETED
            ):
                return False
        return True

    def save_comparison(
        self, comparison: DocumentComparison, user_id: str
    ) -> DocumentComparison:
        with self._lock:
            if comparison.user_id != user_id:
                raise ValueError("Unauthorized comparison user ownership mismatch.")
            if not self._verify_documents_ownership(comparison.document_ids, user_id):
                raise ValueError("Unauthorized document ownership in comparison.")
            self._comparisons[comparison.id] = comparison
            return comparison

    def get_comparison_by_id(
        self, comparison_id: str, user_id: str
    ) -> DocumentComparison | None:
        with self._lock:
            comp = self._comparisons.get(comparison_id)
            if not comp or comp.user_id != user_id:
                return None
            if not self._verify_documents_ownership(comp.document_ids, user_id):
                return None
            return comp

    def list_comparisons_for_user(self, user_id: str) -> list[DocumentComparison]:
        with self._lock:
            results = [
                c
                for c in self._comparisons.values()
                if c.user_id == user_id
                and self._verify_documents_ownership(c.document_ids, user_id)
            ]
            results.sort(key=lambda c: c.created_at, reverse=True)
            return results

    def delete_comparison(self, comparison_id: str, user_id: str) -> bool:
        with self._lock:
            comp = self._comparisons.get(comparison_id)
            if not comp or comp.user_id != user_id:
                return False
            del self._comparisons[comparison_id]
            return True

    def delete_comparisons_for_document(self, document_id: str, user_id: str) -> int:
        with self._lock:
            to_delete = [
                cid
                for cid, comp in self._comparisons.items()
                if comp.user_id == user_id and document_id in comp.document_ids
            ]
            for cid in to_delete:
                del self._comparisons[cid]
            return len(to_delete)


class PostgresComparisonRepository(ComparisonRepository):
    """PostgreSQL repository for Document Comparison persistence with JSONB storage."""

    def __init__(
        self,
        db_connection_factory: Any = get_db_connection,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self._get_connection = db_connection_factory
        self._doc_repo = document_repository or in_memory_document_repository

    def _verify_documents_ownership(
        self, document_ids: list[str], user_id: str
    ) -> bool:
        for doc_id in document_ids:
            doc = self._doc_repo.get_by_id(doc_id)
            if (
                doc is None
                or doc.user_id != user_id
                or doc.status == DocumentStatus.DELETED
            ):
                return False
        return True

    def save_comparison(
        self, comparison: DocumentComparison, user_id: str
    ) -> DocumentComparison:
        if comparison.user_id != user_id:
            raise ValueError("Unauthorized comparison user ownership mismatch.")
        if not self._verify_documents_ownership(comparison.document_ids, user_id):
            raise ValueError("Unauthorized document ownership in comparison.")

        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                payload = {
                    "documents": [d.to_dict() for d in comparison.documents],
                    "findings": [f.to_dict() for f in comparison.findings],
                    "summary": comparison.summary.to_dict(),
                }
                cur.execute(
                    """
                    INSERT INTO document_comparisons (
                        id, user_id, title, document_ids,
                        comparison_data, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        document_ids = EXCLUDED.document_ids,
                        comparison_data = EXCLUDED.comparison_data,
                        updated_at = EXCLUDED.updated_at;
                    """,
                    (
                        comparison.id,
                        comparison.user_id,
                        comparison.title,
                        json.dumps(comparison.document_ids),
                        json.dumps(payload),
                        comparison.created_at,
                        comparison.updated_at,
                    ),
                )
            conn.commit()
            return comparison
        finally:
            conn.close()

    def get_comparison_by_id(
        self, comparison_id: str, user_id: str
    ) -> DocumentComparison | None:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, title, document_ids,
                           comparison_data, created_at, updated_at
                    FROM document_comparisons
                    WHERE id = %s AND user_id = %s;
                    """,
                    (comparison_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None

                doc_ids = row[3] if isinstance(row[3], list) else json.loads(row[3])
                if not self._verify_documents_ownership(doc_ids, user_id):
                    return None

                comp_data = row[4] if isinstance(row[4], dict) else json.loads(row[4])
                data = {
                    "id": str(row[0]),
                    "user_id": str(row[1]),
                    "title": row[2],
                    "document_ids": doc_ids,
                    "documents": comp_data.get("documents", []),
                    "findings": comp_data.get("findings", []),
                    "summary": comp_data.get("summary", {}),
                    "created_at": row[5],
                    "updated_at": row[6],
                }
                return DocumentComparison.from_dict(data)
        finally:
            conn.close()

    def list_comparisons_for_user(self, user_id: str) -> list[DocumentComparison]:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, title, document_ids,
                           comparison_data, created_at, updated_at
                    FROM document_comparisons
                    WHERE user_id = %s
                    ORDER BY created_at DESC;
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
                results: list[DocumentComparison] = []
                for row in rows:
                    doc_ids = row[3] if isinstance(row[3], list) else json.loads(row[3])
                    if not self._verify_documents_ownership(doc_ids, user_id):
                        continue
                    comp_data = (
                        row[4] if isinstance(row[4], dict) else json.loads(row[4])
                    )
                    data = {
                        "id": str(row[0]),
                        "user_id": str(row[1]),
                        "title": row[2],
                        "document_ids": doc_ids,
                        "documents": comp_data.get("documents", []),
                        "findings": comp_data.get("findings", []),
                        "summary": comp_data.get("summary", {}),
                        "created_at": row[5],
                        "updated_at": row[6],
                    }
                    results.append(DocumentComparison.from_dict(data))
                return results
        finally:
            conn.close()

    def delete_comparison(self, comparison_id: str, user_id: str) -> bool:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_comparisons
                    WHERE id = %s AND user_id = %s;
                    """,
                    (comparison_id, user_id),
                )
                deleted = bool(cur.rowcount > 0)
            conn.commit()
            return deleted
        finally:
            conn.close()

    def delete_comparisons_for_document(self, document_id: str, user_id: str) -> int:
        conn: connection = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM document_comparisons
                    WHERE user_id = %s AND document_ids ? %s;
                    """,
                    (user_id, document_id),
                )
                deleted_count = int(cur.rowcount)
            conn.commit()
            return deleted_count
        finally:
            conn.close()


# Default singleton instance
in_memory_comparison_repository = InMemoryComparisonRepository()
