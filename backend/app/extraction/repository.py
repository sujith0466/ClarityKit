from abc import ABC, abstractmethod
from threading import Lock

from app.database import get_db_connection
from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.extraction.models import (
    DocumentUnderstanding,
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
    ExtractedReviewFlag,
)


class ExtractionRepository(ABC):
    """Abstract interface for structured extraction storage and retrieval."""

    @abstractmethod
    def save_understanding(
        self,
        document_id: str,
        parties: list[ExtractedParty],
        clauses: list[ExtractedClause],
        obligations: list[ExtractedObligation],
        dates: list[ExtractedDate],
        review_flags: list[ExtractedReviewFlag],
        provider_info: dict | None = None,
    ) -> DocumentUnderstanding:
        """Atomically persist extracted entities, replacing previous records."""
        pass

    @abstractmethod
    def get_understanding_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> DocumentUnderstanding | None:
        """Retrieve structured extraction facts for a document with tenant check."""
        pass

    @abstractmethod
    def delete_understanding_by_document(self, document_id: str) -> int:
        """Delete all extraction facts for a document."""
        pass

    @abstractmethod
    def has_understanding(self, document_id: str) -> bool:
        """Check if extraction records exist for a document."""
        pass


class InMemoryExtractionRepository(ExtractionRepository):
    """Thread-safe in-memory extraction repository for testing and offline execution."""

    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self._lock = Lock()
        self._doc_repo = document_repository or in_memory_document_repository
        self._parties: dict[str, list[ExtractedParty]] = {}
        self._clauses: dict[str, list[ExtractedClause]] = {}
        self._obligations: dict[str, list[ExtractedObligation]] = {}
        self._dates: dict[str, list[ExtractedDate]] = {}
        self._review_flags: dict[str, list[ExtractedReviewFlag]] = {}
        self._provider_infos: dict[str, dict] = {}

    def save_understanding(
        self,
        document_id: str,
        parties: list[ExtractedParty],
        clauses: list[ExtractedClause],
        obligations: list[ExtractedObligation],
        dates: list[ExtractedDate],
        review_flags: list[ExtractedReviewFlag],
        provider_info: dict | None = None,
    ) -> DocumentUnderstanding:
        with self._lock:
            self._parties[document_id] = list(parties)
            self._clauses[document_id] = list(clauses)
            self._obligations[document_id] = list(obligations)
            self._dates[document_id] = list(dates)
            self._review_flags[document_id] = list(review_flags)
            self._provider_infos[document_id] = provider_info or {}

            return DocumentUnderstanding(
                document_id=document_id,
                parties=self._parties[document_id],
                clauses=self._clauses[document_id],
                obligations=self._obligations[document_id],
                dates=self._dates[document_id],
                review_flags=self._review_flags[document_id],
                provider_info=self._provider_infos[document_id],
            )

    def get_understanding_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> DocumentUnderstanding | None:
        with self._lock:
            if user_id is not None:
                doc = self._doc_repo.get_by_id(document_id)
                if (
                    doc is None
                    or doc.user_id != user_id
                    or doc.status == DocumentStatus.DELETED
                ):
                    return None

            if (
                document_id not in self._parties
                and document_id not in self._clauses
                and document_id not in self._obligations
                and document_id not in self._dates
                and document_id not in self._review_flags
            ):
                return None

            return DocumentUnderstanding(
                document_id=document_id,
                parties=self._parties.get(document_id, []),
                clauses=self._clauses.get(document_id, []),
                obligations=self._obligations.get(document_id, []),
                dates=self._dates.get(document_id, []),
                review_flags=self._review_flags.get(document_id, []),
                provider_info=self._provider_infos.get(document_id, {}),
            )

    def delete_understanding_by_document(self, document_id: str) -> int:
        with self._lock:
            count = 0
            if document_id in self._parties:
                count += len(self._parties.pop(document_id))
            if document_id in self._clauses:
                count += len(self._clauses.pop(document_id))
            if document_id in self._obligations:
                count += len(self._obligations.pop(document_id))
            if document_id in self._dates:
                count += len(self._dates.pop(document_id))
            if document_id in self._review_flags:
                count += len(self._review_flags.pop(document_id))
            self._provider_infos.pop(document_id, None)
            return count

    def has_understanding(self, document_id: str) -> bool:
        with self._lock:
            return (
                document_id in self._parties
                or document_id in self._clauses
                or document_id in self._obligations
                or document_id in self._dates
                or document_id in self._review_flags
            )


class PgExtractionRepository(ExtractionRepository):
    """PostgreSQL implementation of ExtractionRepository with tenant isolation."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url

    def _get_conn(self):  # type: ignore[no-untyped-def]
        return get_db_connection(self._database_url)

    def save_understanding(
        self,
        document_id: str,
        parties: list[ExtractedParty],
        clauses: list[ExtractedClause],
        obligations: list[ExtractedObligation],
        dates: list[ExtractedDate],
        review_flags: list[ExtractedReviewFlag],
        provider_info: dict | None = None,
    ) -> DocumentUnderstanding:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    # 1. Atomic clear existing records
                    cur.execute(
                        "DELETE FROM extracted_parties WHERE document_id = %s;",
                        (document_id,),
                    )
                    cur.execute(
                        "DELETE FROM extracted_clauses WHERE document_id = %s;",
                        (document_id,),
                    )
                    cur.execute(
                        "DELETE FROM extracted_obligations WHERE document_id = %s;",
                        (document_id,),
                    )
                    cur.execute(
                        "DELETE FROM extracted_dates WHERE document_id = %s;",
                        (document_id,),
                    )
                    cur.execute(
                        "DELETE FROM extracted_review_flags WHERE document_id = %s;",
                        (document_id,),
                    )

                    # 2. Insert Parties
                    for p in parties:
                        cur.execute(
                            """
                            INSERT INTO extracted_parties (
                                id, document_id, name, role, page_number,
                                source_span, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                            """,
                            (
                                p.id,
                                p.document_id,
                                p.name,
                                p.role,
                                p.page_number,
                                p.source_span,
                                p.created_at,
                            ),
                        )

                    # 3. Insert Clauses
                    for c in clauses:
                        cur.execute(
                            """
                            INSERT INTO extracted_clauses (
                                id, document_id, clause_identifier, title,
                                category, text, page_start, page_end,
                                source_span, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """,
                            (
                                c.id,
                                c.document_id,
                                c.clause_identifier,
                                c.title,
                                c.category,
                                c.text,
                                c.page_start,
                                c.page_end,
                                c.source_span,
                                c.created_at,
                            ),
                        )

                    # 4. Insert Obligations
                    for o in obligations:
                        cur.execute(
                            """
                            INSERT INTO extracted_obligations (
                                id, document_id, clause_id, obligor, duty,
                                trigger, deadline, page_start, page_end,
                                source_span, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """,
                            (
                                o.id,
                                o.document_id,
                                o.clause_id,
                                o.obligor,
                                o.duty,
                                o.trigger,
                                o.deadline,
                                o.page_start,
                                o.page_end,
                                o.source_span,
                                o.created_at,
                            ),
                        )

                    # 5. Insert Dates
                    for d in dates:
                        cur.execute(
                            """
                            INSERT INTO extracted_dates (
                                id, document_id, date_type, raw_text,
                                normalized_date, description, page_number,
                                source_span, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """,
                            (
                                d.id,
                                d.document_id,
                                d.date_type,
                                d.raw_text,
                                d.normalized_date,
                                d.description,
                                d.page_number,
                                d.source_span,
                                d.created_at,
                            ),
                        )

                    # 6. Insert Review Flags
                    for f in review_flags:
                        cur.execute(
                            """
                            INSERT INTO extracted_review_flags (
                                id, document_id, related_clause_id, flag_type,
                                title, description, severity, page_start,
                                page_end, source_span, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                            """,
                            (
                                f.id,
                                f.document_id,
                                f.related_clause_id,
                                f.flag_type,
                                f.title,
                                f.description,
                                f.severity,
                                f.page_start,
                                f.page_end,
                                f.source_span,
                                f.created_at,
                            ),
                        )

            return DocumentUnderstanding(
                document_id=document_id,
                parties=parties,
                clauses=clauses,
                obligations=obligations,
                dates=dates,
                review_flags=review_flags,
                provider_info=provider_info or {},
            )
        finally:
            conn.close()

    def get_understanding_by_document(
        self, document_id: str, user_id: str | None = None
    ) -> DocumentUnderstanding | None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # 1. Tenant ownership validation
                if user_id is not None:
                    cur.execute(
                        """
                        SELECT id FROM documents
                        WHERE id = %s AND user_id = %s AND status != 'deleted';
                        """,
                        (document_id, user_id),
                    )
                    if cur.fetchone() is None:
                        return None

                # 2. Query Parties
                cur.execute(
                    """
                    SELECT id, document_id, name, role, page_number,
                           source_span, created_at
                    FROM extracted_parties
                    WHERE document_id = %s
                    ORDER BY page_number ASC;
                    """,
                    (document_id,),
                )
                party_rows = cur.fetchall()
                parties = [
                    ExtractedParty(
                        id=str(r[0]),
                        document_id=str(r[1]),
                        name=str(r[2]),
                        role=str(r[3]),
                        page_number=int(r[4]),
                        source_span=str(r[5]),
                        created_at=str(r[6]),
                    )
                    for r in party_rows
                ]

                # 3. Query Clauses
                cur.execute(
                    """
                    SELECT id, document_id, clause_identifier, title, category,
                           text, page_start, page_end, source_span, created_at
                    FROM extracted_clauses
                    WHERE document_id = %s
                    ORDER BY page_start ASC, clause_identifier ASC;
                    """,
                    (document_id,),
                )
                clause_rows = cur.fetchall()
                clauses = [
                    ExtractedClause(
                        id=str(r[0]),
                        document_id=str(r[1]),
                        clause_identifier=str(r[2]),
                        title=str(r[3]),
                        category=str(r[4]),
                        text=str(r[5]),
                        page_start=int(r[6]),
                        page_end=int(r[7]),
                        source_span=str(r[8]),
                        created_at=str(r[9]),
                    )
                    for r in clause_rows
                ]

                # 4. Query Obligations
                cur.execute(
                    """
                    SELECT id, document_id, clause_id, obligor, duty, trigger,
                           deadline, page_start, page_end, source_span, created_at
                    FROM extracted_obligations
                    WHERE document_id = %s
                    ORDER BY page_start ASC;
                    """,
                    (document_id,),
                )
                obligation_rows = cur.fetchall()
                obligations = [
                    ExtractedObligation(
                        id=str(r[0]),
                        document_id=str(r[1]),
                        clause_id=str(r[2]) if r[2] is not None else None,
                        obligor=str(r[3]),
                        duty=str(r[4]),
                        trigger=str(r[5]) if r[5] is not None else None,
                        deadline=str(r[6]) if r[6] is not None else None,
                        page_start=int(r[7]),
                        page_end=int(r[8]),
                        source_span=str(r[9]),
                        created_at=str(r[10]),
                    )
                    for r in obligation_rows
                ]

                # 5. Query Dates
                cur.execute(
                    """
                    SELECT id, document_id, date_type, raw_text, normalized_date,
                           description, page_number, source_span, created_at
                    FROM extracted_dates
                    WHERE document_id = %s
                    ORDER BY page_number ASC;
                    """,
                    (document_id,),
                )
                date_rows = cur.fetchall()
                dates = [
                    ExtractedDate(
                        id=str(r[0]),
                        document_id=str(r[1]),
                        date_type=str(r[2]),
                        raw_text=str(r[3]),
                        normalized_date=str(r[4]) if r[4] is not None else None,
                        description=str(r[5]),
                        page_number=int(r[6]),
                        source_span=str(r[7]),
                        created_at=str(r[8]),
                    )
                    for r in date_rows
                ]

                # 6. Query Review Flags
                cur.execute(
                    """
                    SELECT id, document_id, related_clause_id, flag_type,
                           title, description, severity, page_start, page_end,
                           source_span, created_at
                    FROM extracted_review_flags
                    WHERE document_id = %s
                    ORDER BY page_start ASC;
                    """,
                    (document_id,),
                )
                flag_rows = cur.fetchall()
                review_flags = [
                    ExtractedReviewFlag(
                        id=str(r[0]),
                        document_id=str(r[1]),
                        related_clause_id=str(r[2]) if r[2] is not None else None,
                        flag_type=str(r[3]),
                        title=str(r[4]),
                        description=str(r[5]),
                        severity=str(r[6]),
                        page_start=int(r[7]),
                        page_end=int(r[8]),
                        source_span=str(r[9]),
                        created_at=str(r[10]),
                    )
                    for r in flag_rows
                ]

                if not (parties or clauses or obligations or dates or review_flags):
                    return None

                return DocumentUnderstanding(
                    document_id=document_id,
                    parties=parties,
                    clauses=clauses,
                    obligations=obligations,
                    dates=dates,
                    review_flags=review_flags,
                )
        finally:
            conn.close()

    def delete_understanding_by_document(self, document_id: str) -> int:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM extracted_parties WHERE document_id = %s;",
                        (document_id,),
                    )
                    c1 = cur.rowcount
                    cur.execute(
                        "DELETE FROM extracted_clauses WHERE document_id = %s;",
                        (document_id,),
                    )
                    c2 = cur.rowcount
                    cur.execute(
                        "DELETE FROM extracted_obligations WHERE document_id = %s;",
                        (document_id,),
                    )
                    c3 = cur.rowcount
                    cur.execute(
                        "DELETE FROM extracted_dates WHERE document_id = %s;",
                        (document_id,),
                    )
                    c4 = cur.rowcount
                    cur.execute(
                        "DELETE FROM extracted_review_flags WHERE document_id = %s;",
                        (document_id,),
                    )
                    c5 = cur.rowcount
                    return int(c1 + c2 + c3 + c4 + c5)
        finally:
            conn.close()

    def has_understanding(self, document_id: str) -> bool:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT (
                        EXISTS(
                            SELECT 1 FROM extracted_parties WHERE document_id = %s
                        ) OR
                        EXISTS(
                            SELECT 1 FROM extracted_clauses WHERE document_id = %s
                        ) OR
                        EXISTS(
                            SELECT 1 FROM extracted_obligations WHERE document_id = %s
                        ) OR
                        EXISTS(
                            SELECT 1 FROM extracted_dates WHERE document_id = %s
                        ) OR
                        EXISTS(
                            SELECT 1 FROM extracted_review_flags WHERE document_id = %s
                        )
                    );
                    """,
                    (document_id, document_id, document_id, document_id, document_id),
                )
                row = cur.fetchone()
                return bool(row and row[0])
        finally:
            conn.close()


# Global singleton repository instance for in-memory runtime
in_memory_extraction_repository = InMemoryExtractionRepository()


def get_extraction_repository() -> ExtractionRepository:
    """Return active ExtractionRepository instance."""
    from app.config import Config

    if Config.DATABASE_URL:
        return PgExtractionRepository(Config.DATABASE_URL)
    return in_memory_extraction_repository
