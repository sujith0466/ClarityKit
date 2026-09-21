import json
import logging
from abc import ABC, abstractmethod
from threading import Lock

from psycopg2.extensions import connection

from app.brief.models import BRIEF_DEFAULT_DISCLAIMER, LawyerPreparationBrief
from app.database import get_db_connection
from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository

logger = logging.getLogger(__name__)


class BriefRepository(ABC):
    """Abstract repository for Lawyer-Preparation Brief persistence."""

    @abstractmethod
    def save_brief(
        self, brief: LawyerPreparationBrief, user_id: str
    ) -> LawyerPreparationBrief:
        """Persist or update a preparation brief."""
        pass

    @abstractmethod
    def get_brief_by_id(
        self, brief_id: str, user_id: str
    ) -> LawyerPreparationBrief | None:
        """Retrieve a brief by ID enforcing document ownership."""
        pass

    @abstractmethod
    def get_latest_brief_by_document(
        self, document_id: str, user_id: str
    ) -> LawyerPreparationBrief | None:
        """Retrieve the latest brief for an owned document."""
        pass

    @abstractmethod
    def delete_brief(self, brief_id: str, user_id: str) -> bool:
        """Delete a brief by ID enforcing document ownership."""
        pass


class InMemoryBriefRepository(BriefRepository):
    """Thread-safe in-memory repository for preparation briefs."""

    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._lock = Lock()
        self._doc_repo = document_repository or in_memory_document_repository
        # Key: brief_id -> LawyerPreparationBrief
        self._briefs: dict[str, LawyerPreparationBrief] = {}

    def clear(self) -> None:
        with self._lock:
            self._briefs.clear()

    def _verify_document_ownership(self, document_id: str, user_id: str) -> bool:
        doc = self._doc_repo.get_by_id(document_id)
        return (
            doc is not None
            and doc.user_id == user_id
            and doc.status != DocumentStatus.DELETED
        )

    def save_brief(
        self, brief: LawyerPreparationBrief, user_id: str
    ) -> LawyerPreparationBrief:
        with self._lock:
            if not self._verify_document_ownership(brief.document_id, user_id):
                raise ValueError("Unauthorized document ownership.")
            self._briefs[brief.id] = brief
            return brief

    def get_brief_by_id(
        self, brief_id: str, user_id: str
    ) -> LawyerPreparationBrief | None:
        with self._lock:
            brief = self._briefs.get(brief_id)
            if not brief:
                return None
            if not self._verify_document_ownership(brief.document_id, user_id):
                return None
            return brief

    def get_latest_brief_by_document(
        self, document_id: str, user_id: str
    ) -> LawyerPreparationBrief | None:
        with self._lock:
            if not self._verify_document_ownership(document_id, user_id):
                return None
            matching = [
                b for b in self._briefs.values() if b.document_id == document_id
            ]
            if not matching:
                return None
            # Sort by created_at descending
            matching.sort(key=lambda b: b.created_at, reverse=True)
            return matching[0]

    def delete_brief(self, brief_id: str, user_id: str) -> bool:
        with self._lock:
            brief = self._briefs.get(brief_id)
            if not brief:
                return False
            if not self._verify_document_ownership(brief.document_id, user_id):
                return False
            del self._briefs[brief_id]
            return True


class PostgresBriefRepository(BriefRepository):
    """PostgreSQL preparation brief repository with SQL multi-tenant isolation."""

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url

    def _get_connection(self) -> connection:
        return get_db_connection(self._db_url)

    def save_brief(
        self, brief: LawyerPreparationBrief, user_id: str
    ) -> LawyerPreparationBrief:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # 1. Verify tenant ownership
                cur.execute(
                    """
                    SELECT id FROM documents
                    WHERE id = %s AND user_id = %s AND status != 'DELETED';
                    """,
                    (brief.document_id, user_id),
                )
                if not cur.fetchone():
                    raise ValueError("Document not found or access denied.")

                sections_payload = {
                    "sections": {k: s.to_dict() for k, s in brief.sections.items()},
                    "questions_for_lawyer": [
                        q.to_dict() for q in brief.questions_for_lawyer
                    ],
                    "facts_to_confirm": brief.facts_to_confirm,
                    "documents_to_bring": brief.documents_to_bring,
                    "open_questions": brief.open_questions,
                    "completeness_score": brief.completeness_score,
                    "disclaimer": brief.disclaimer,
                }
                sections_json = json.dumps(sections_payload)
                ev_refs_json = json.dumps(brief.evidence_references)

                cur.execute(
                    """
                    INSERT INTO preparation_briefs (
                        id, document_id, title, situation_summary,
                        sections, evidence_references, is_grounded,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        situation_summary = EXCLUDED.situation_summary,
                        sections = EXCLUDED.sections,
                        evidence_references = EXCLUDED.evidence_references,
                        is_grounded = EXCLUDED.is_grounded,
                        updated_at = EXCLUDED.updated_at;
                    """,
                    (
                        brief.id,
                        brief.document_id,
                        brief.title,
                        brief.situation_summary,
                        sections_json,
                        ev_refs_json,
                        brief.is_grounded,
                        brief.created_at,
                        brief.updated_at,
                    ),
                )
                conn.commit()
                return brief
        finally:
            conn.close()

    def get_brief_by_id(
        self, brief_id: str, user_id: str
    ) -> LawyerPreparationBrief | None:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT b.id, b.document_id, b.title, b.situation_summary,
                           b.sections, b.evidence_references, b.is_grounded,
                           b.created_at, b.updated_at
                    FROM preparation_briefs b
                    JOIN documents d ON d.id = b.document_id
                    WHERE b.id = %s AND d.user_id = %s AND d.status != 'DELETED';
                    """,
                    (brief_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_brief(row)
        finally:
            conn.close()

    def get_latest_brief_by_document(
        self, document_id: str, user_id: str
    ) -> LawyerPreparationBrief | None:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT b.id, b.document_id, b.title, b.situation_summary,
                           b.sections, b.evidence_references, b.is_grounded,
                           b.created_at, b.updated_at
                    FROM preparation_briefs b
                    JOIN documents d ON d.id = b.document_id
                    WHERE b.document_id = %s
                      AND d.user_id = %s
                      AND d.status != 'DELETED'
                    ORDER BY b.created_at DESC
                    LIMIT 1;
                    """,
                    (document_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_brief(row)
        finally:
            conn.close()

    def delete_brief(self, brief_id: str, user_id: str) -> bool:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM preparation_briefs b
                    USING documents d
                    WHERE b.document_id = d.id
                      AND b.id = %s
                      AND d.user_id = %s
                    RETURNING b.id;
                    """,
                    (brief_id, user_id),
                )
                deleted = cur.fetchone() is not None
                conn.commit()
                return deleted
        finally:
            conn.close()

    def _row_to_brief(self, row: tuple) -> LawyerPreparationBrief:
        raw_sections = row[4]
        if isinstance(raw_sections, str):
            raw_sections = json.loads(raw_sections)

        raw_ev = row[5]
        if isinstance(raw_ev, str):
            raw_ev = json.loads(raw_ev)

        if isinstance(raw_sections, dict) and "sections" in raw_sections:
            sec_map = raw_sections.get("sections", {})
            questions = raw_sections.get("questions_for_lawyer", [])
            facts = raw_sections.get("facts_to_confirm", [])
            docs = raw_sections.get("documents_to_bring", [])
            open_q = raw_sections.get("open_questions", [])
            score = raw_sections.get("completeness_score", 1.0)
            disclaimer = raw_sections.get("disclaimer", BRIEF_DEFAULT_DISCLAIMER)
        else:
            sec_map = raw_sections if isinstance(raw_sections, dict) else {}
            questions = []
            facts = []
            docs = []
            open_q = []
            score = 1.0
            disclaimer = BRIEF_DEFAULT_DISCLAIMER

        data = {
            "id": str(row[0]),
            "document_id": str(row[1]),
            "title": row[2],
            "situation_summary": row[3],
            "sections": sec_map,
            "questions_for_lawyer": questions,
            "facts_to_confirm": facts,
            "documents_to_bring": docs,
            "open_questions": open_q,
            "completeness_score": score,
            "disclaimer": disclaimer,
            "evidence_references": raw_ev,
            "is_grounded": row[6],
            "created_at": row[7].isoformat()
            if hasattr(row[7], "isoformat")
            else str(row[7]),
            "updated_at": row[8].isoformat()
            if hasattr(row[8], "isoformat")
            else str(row[8]),
        }
        return LawyerPreparationBrief.from_dict(data)


in_memory_brief_repository = InMemoryBriefRepository()


def get_brief_repository(db_url: str | None = None) -> BriefRepository:
    """Factory helper to obtain the configured BriefRepository."""
    import os

    effective_url = db_url or os.getenv("DATABASE_URL")
    if effective_url:
        return PostgresBriefRepository(effective_url)
    return in_memory_brief_repository
