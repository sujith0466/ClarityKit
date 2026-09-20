import logging
import threading
import uuid
from abc import ABC, abstractmethod

from psycopg2.extras import RealDictCursor

from app.config import Config
from app.database import get_db_connection
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.evidence.models import (
    Claim,
    ClaimType,
    DocumentEvidenceReport,
    EvidenceCoverage,
    EvidenceMatchType,
    EvidenceReference,
    EvidenceValidationStatus,
)

logger = logging.getLogger(__name__)


class EvidenceRepository(ABC):
    """Abstract interface for persisting and querying evidence records."""

    @abstractmethod
    def save_evidence_report(self, report: DocumentEvidenceReport) -> None:
        """Atomically save or replace evidence records for a document."""
        pass

    @abstractmethod
    def get_evidence_report(
        self, document_id: str, user_id: str
    ) -> DocumentEvidenceReport | None:
        """Retrieve evidence report with tenant ownership verification."""
        pass

    @abstractmethod
    def delete_by_document(self, document_id: str) -> int:
        """Delete all evidence records for a document."""
        pass


class InMemoryEvidenceRepository(EvidenceRepository):
    """Thread-safe in-memory repository for development and isolated testing."""

    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._lock = threading.Lock()
        self._doc_repo = document_repository or in_memory_document_repository
        self._reports: dict[str, DocumentEvidenceReport] = {}

    def save_evidence_report(self, report: DocumentEvidenceReport) -> None:
        with self._lock:
            self._reports[report.document_id] = report

    def get_evidence_report(
        self, document_id: str, user_id: str
    ) -> DocumentEvidenceReport | None:
        with self._lock:
            doc = self._doc_repo.get_by_id(document_id)
            if doc is not None and doc.user_id != user_id:
                return None
            return self._reports.get(document_id)

    def delete_by_document(self, document_id: str) -> int:
        with self._lock:
            if document_id in self._reports:
                del self._reports[document_id]
                return 1
            return 0

    def clear(self) -> None:
        with self._lock:
            self._reports.clear()


class PgEvidenceRepository(EvidenceRepository):
    """PostgreSQL repository with SQL-level multi-tenant isolation."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url

    def _get_conn(self):  # type: ignore[no-untyped-def]
        return get_db_connection(self._database_url)

    def save_evidence_report(self, report: DocumentEvidenceReport) -> None:
        """Replace evidence records for document in an atomic transaction."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM document_evidence_records WHERE document_id = %s;",
                        (report.document_id,),
                    )

                    insert_query = """
                        INSERT INTO document_evidence_records (
                            id, document_id, claim_id, claim_type, claim_text,
                            entity_id, page_start, page_end, source_span,
                            source_text, char_start, char_end, match_type,
                            validation_status, validation_reason, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s
                        );
                    """
                    for c in report.claims:
                        ref = c.evidence
                        record_id = str(uuid.uuid4())
                        page_start = ref.page_start if ref else 1
                        page_end = ref.page_end if ref else 1
                        source_span = ref.source_span if ref else ""
                        source_text = ref.source_text if ref else None
                        char_start = ref.char_start if ref else None
                        char_end = ref.char_end if ref else None
                        match_type = (
                            ref.match_type.value
                            if ref
                            else EvidenceMatchType.UNMATCHED.value
                        )
                        val_status = (
                            ref.validation_status.value
                            if ref
                            else EvidenceValidationStatus.INVALID.value
                        )
                        val_reason = (
                            ref.validation_reason if ref else "MISSING_EVIDENCE"
                        )

                        cur.execute(
                            insert_query,
                            (
                                record_id,
                                report.document_id,
                                c.id,
                                c.claim_type.value,
                                c.claim_text,
                                c.entity_id,
                                page_start,
                                page_end,
                                source_span,
                                source_text,
                                char_start,
                                char_end,
                                match_type,
                                val_status,
                                val_reason,
                                report.generated_at,
                            ),
                        )
        finally:
            conn.close()

    def get_evidence_report(
        self, document_id: str, user_id: str
    ) -> DocumentEvidenceReport | None:
        """Fetch evidence records ensuring SQL-level tenant isolation."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT
                            r.id, r.document_id, r.claim_id, r.claim_type,
                            r.claim_text, r.entity_id, r.page_start, r.page_end,
                            r.source_span, r.source_text, r.char_start,
                            r.char_end, r.match_type, r.validation_status,
                            r.validation_reason, r.created_at
                        FROM document_evidence_records r
                        JOIN documents d ON d.id = r.document_id
                        WHERE r.document_id = %s AND d.user_id = %s
                        ORDER BY r.page_start ASC, r.created_at ASC;
                    """
                    cur.execute(query, (document_id, user_id))
                    rows = cur.fetchall()

                    if not rows:
                        return None

                    claims: list[Claim] = []
                    generated_at = (
                        rows[0]["created_at"].isoformat()
                        if rows[0].get("created_at")
                        else ""
                    )

                    for row in rows:
                        match_type = (
                            EvidenceMatchType(row["match_type"])
                            if row["match_type"] in [m.value for m in EvidenceMatchType]
                            else EvidenceMatchType.UNMATCHED
                        )
                        val_status = (
                            EvidenceValidationStatus(row["validation_status"])
                            if row["validation_status"]
                            in [s.value for s in EvidenceValidationStatus]
                            else EvidenceValidationStatus.UNVERIFIED
                        )
                        claim_type = (
                            ClaimType(row["claim_type"])
                            if row["claim_type"] in [c.value for c in ClaimType]
                            else ClaimType.GENERAL_FACT
                        )

                        ref = EvidenceReference(
                            document_id=str(row["document_id"]),
                            page_start=row["page_start"],
                            page_end=row["page_end"],
                            source_span=row["source_span"],
                            source_text=row["source_text"],
                            char_start=row["char_start"],
                            char_end=row["char_end"],
                            match_type=match_type,
                            validation_status=val_status,
                            validation_reason=row["validation_reason"],
                        )

                        claim = Claim(
                            id=str(row["claim_id"]),
                            document_id=str(row["document_id"]),
                            claim_text=row["claim_text"],
                            claim_type=claim_type,
                            entity_id=(
                                str(row["entity_id"]) if row.get("entity_id") else None
                            ),
                            evidence=ref,
                            validation_status=val_status,
                        )
                        claims.append(claim)

                    coverage = EvidenceCoverage.calculate(claims)
                    return DocumentEvidenceReport(
                        document_id=document_id,
                        claims=claims,
                        coverage=coverage,
                        generated_at=generated_at,
                    )
        finally:
            conn.close()

    def delete_by_document(self, document_id: str) -> int:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM document_evidence_records WHERE document_id = %s;",
                        (document_id,),
                    )
                    deleted = cur.rowcount
                    return int(deleted or 0)
        finally:
            conn.close()


in_memory_evidence_repository = InMemoryEvidenceRepository()


def get_evidence_repository() -> EvidenceRepository:
    """Factory returning repository based on database configuration."""
    if Config.DATABASE_URL:
        return PgEvidenceRepository(Config.DATABASE_URL)
    return in_memory_evidence_repository
