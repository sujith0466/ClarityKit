import os
import uuid
from collections.abc import Generator

import pytest

from app.database import get_db_connection, run_migrations
from app.extraction.models import (
    ExtractedClause,
    ExtractedDate,
    ExtractedObligation,
    ExtractedParty,
    ExtractedReviewFlag,
)
from app.extraction.repository import PgExtractionRepository

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="Live PostgreSQL DATABASE_URL not set")
class TestExtractionPgIntegration:
    """T-106: Live PostgreSQL integration tests for Structured Extraction tables."""

    @pytest.fixture(autouse=True)
    def setup_live_db(self) -> Generator[None, None, None]:
        assert DATABASE_URL is not None
        # Ensure migration 0003 is applied
        run_migrations(DATABASE_URL)
        self.repo = PgExtractionRepository(DATABASE_URL)
        self.conn = get_db_connection(DATABASE_URL)

        self.user_a = str(uuid.uuid4())
        self.user_b = str(uuid.uuid4())
        self.doc_a = str(uuid.uuid4())
        self.doc_b = str(uuid.uuid4())

        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, password_hash, name)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        self.user_a,
                        f"test_ext_a_{self.user_a[:8]}@test.com",
                        "hash",
                        "User A",
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO users (id, email, password_hash, name)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (
                        self.user_b,
                        f"test_ext_b_{self.user_b[:8]}@test.com",
                        "hash",
                        "User B",
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO documents (
                        id, user_id, filename, storage_path,
                        size_bytes, content_type, sha256_hash, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        self.doc_a,
                        self.user_a,
                        "lease_a.pdf",
                        "path/a",
                        1024,
                        "application/pdf",
                        "hash_ext_a",
                        "ready",
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO documents (
                        id, user_id, filename, storage_path,
                        size_bytes, content_type, sha256_hash, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        self.doc_b,
                        self.user_b,
                        "nda_b.pdf",
                        "path/b",
                        1024,
                        "application/pdf",
                        "hash_ext_b",
                        "ready",
                    ),
                )

        yield

        # Teardown / Cleanup
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM documents WHERE id IN (%s, %s);",
                    (self.doc_a, self.doc_b),
                )
                cur.execute(
                    "DELETE FROM users WHERE id IN (%s, %s);",
                    (self.user_a, self.user_b),
                )
        self.conn.close()

    def test_live_extraction_persistence_and_query(self) -> None:
        """Test persisting structured legal facts in PostgreSQL."""
        party = ExtractedParty.create(
            document_id=self.doc_a,
            name="MegaCorp Inc",
            role="Employer",
            page_number=1,
            source_span='MegaCorp Inc ("Employer")',
        )
        clause = ExtractedClause.create(
            document_id=self.doc_a,
            clause_identifier="Clause-1",
            title="Non-Disclosure",
            category="confidentiality",
            text=(
                "Employee agrees to hold all proprietary information in strict"
                " confidence."
            ),
            page_start=1,
            page_end=1,
            source_span="Clause-1. Non-Disclosure...",
        )
        obligation = ExtractedObligation.create(
            document_id=self.doc_a,
            obligor="Employee",
            duty="shall hold all proprietary information in strict confidence",
            trigger="During and after employment",
            deadline=None,
            page_start=1,
            page_end=1,
            source_span="Employee shall hold all proprietary information...",
            clause_id=clause.id,
        )
        date = ExtractedDate.create(
            document_id=self.doc_a,
            date_type="effective_date",
            raw_text="2026-09-01",
            normalized_date="2026-09-01",
            description="Start date",
            page_number=1,
            source_span="Effective date: 2026-09-01",
        )
        flag = ExtractedReviewFlag.create(
            document_id=self.doc_a,
            flag_type="restrictive_covenant",
            title="Confidentiality Scope",
            description=("Broad confidentiality duration without explicit expiration."),
            severity="low",
            page_start=1,
            page_end=1,
            source_span="in strict confidence perpetually",
            related_clause_id=clause.id,
        )

        saved = self.repo.save_understanding(
            document_id=self.doc_a,
            parties=[party],
            clauses=[clause],
            obligations=[obligation],
            dates=[date],
            review_flags=[flag],
            provider_info={"provider": "live-test"},
        )
        assert saved.document_id == self.doc_a

        # Query back
        understanding = self.repo.get_understanding_by_document(
            self.doc_a, user_id=self.user_a
        )
        assert understanding is not None
        assert len(understanding.parties) == 1
        assert understanding.parties[0].name == "MegaCorp Inc"
        assert len(understanding.clauses) == 1
        assert understanding.clauses[0].category == "confidentiality"
        assert len(understanding.obligations) == 1
        assert understanding.obligations[0].clause_id == clause.id
        assert len(understanding.dates) == 1
        assert len(understanding.review_flags) == 1

    def test_live_extraction_tenant_isolation(self) -> None:
        """Test that User B cannot query User A's extraction understanding."""
        party = ExtractedParty.create(
            document_id=self.doc_a,
            name="Secret Tenant",
            role="Tenant",
            page_number=1,
            source_span="Secret Tenant",
        )
        self.repo.save_understanding(
            document_id=self.doc_a,
            parties=[party],
            clauses=[],
            obligations=[],
            dates=[],
            review_flags=[],
        )

        # User A can access
        assert (
            self.repo.get_understanding_by_document(self.doc_a, self.user_a) is not None
        )

        # User B cannot access (returns None)
        assert self.repo.get_understanding_by_document(self.doc_a, self.user_b) is None

    def test_live_cascade_deletion(self) -> None:
        """Test that deleting a document cascades to delete all extraction rows."""
        party = ExtractedParty.create(
            document_id=self.doc_b,
            name="Temporary Party",
            role="Client",
            page_number=1,
            source_span="Temporary",
        )
        self.repo.save_understanding(
            document_id=self.doc_b,
            parties=[party],
            clauses=[],
            obligations=[],
            dates=[],
            review_flags=[],
        )
        assert self.repo.has_understanding(self.doc_b) is True

        # Delete document row directly
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s;", (self.doc_b,))

        # Extraction rows should be cascaded to 0
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM extracted_parties WHERE document_id = %s;",
                (self.doc_b,),
            )
            count = cur.fetchone()[0]
            assert count == 0
