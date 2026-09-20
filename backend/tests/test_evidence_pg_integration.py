import os
import uuid
from collections.abc import Generator

import pytest

from app.database import get_db_connection, run_migrations
from app.evidence.models import (
    Claim,
    ClaimType,
    DocumentEvidenceReport,
    EvidenceCoverage,
    EvidenceMatchType,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.evidence.repository import PgEvidenceRepository

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="Live PostgreSQL DATABASE_URL not set")
class TestEvidencePgIntegration:
    """Live PostgreSQL integration tests for Evidence Engine tables (Migration 0004)."""

    @pytest.fixture(autouse=True)
    def setup_live_db(self) -> Generator[None, None, None]:
        assert DATABASE_URL is not None
        run_migrations(DATABASE_URL)
        self.repo = PgEvidenceRepository(DATABASE_URL)
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
                        f"test_ev_a_{self.user_a[:8]}@test.com",
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
                        f"test_ev_b_{self.user_b[:8]}@test.com",
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
                        "pg_ev_a.pdf",
                        "path_a",
                        1024,
                        "application/pdf",
                        "hash_a",
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
                        "pg_ev_b.pdf",
                        "path_b",
                        2048,
                        "application/pdf",
                        "hash_b",
                        "ready",
                    ),
                )

        yield

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

    def test_evidence_persistence_and_sql_tenant_isolation(self) -> None:
        ref1 = EvidenceReference(
            document_id=self.doc_a,
            page_start=1,
            page_end=1,
            source_span="Landlord agrees to lease commercial space",
            source_text="Landlord agrees to lease commercial space",
            char_start=0,
            char_end=41,
            match_type=EvidenceMatchType.EXACT,
            validation_status=EvidenceValidationStatus.VALID,
        )
        claim1 = Claim.create(
            document_id=self.doc_a,
            claim_text="Landlord leases commercial space",
            claim_type=ClaimType.OBLIGATION,
            evidence=ref1,
        )

        ref2 = EvidenceReference(
            document_id=self.doc_a,
            page_start=2,
            page_end=2,
            source_span="Invalid span text",
            source_text=None,
            match_type=EvidenceMatchType.UNMATCHED,
            validation_status=EvidenceValidationStatus.INVALID,
            validation_reason="SPAN_NOT_FOUND_ON_PAGE",
        )
        claim2 = Claim.create(
            document_id=self.doc_a,
            claim_text="Rent payment clause",
            claim_type=ClaimType.CLAUSE,
            evidence=ref2,
        )

        claims = [claim1, claim2]
        coverage = EvidenceCoverage.calculate(claims)
        report = DocumentEvidenceReport(
            document_id=self.doc_a,
            claims=claims,
            coverage=coverage,
        )

        self.repo.save_evidence_report(report)

        fetched_a = self.repo.get_evidence_report(self.doc_a, self.user_a)
        assert fetched_a is not None
        assert fetched_a.document_id == self.doc_a
        assert len(fetched_a.claims) == 2
        assert fetched_a.coverage.valid_claims == 1
        assert fetched_a.coverage.invalid_claims == 1
        assert fetched_a.coverage.coverage_ratio == 0.5

        fetched_b = self.repo.get_evidence_report(self.doc_a, self.user_b)
        assert fetched_b is None

    def test_evidence_records_cascade_on_document_delete(self) -> None:
        ref = EvidenceReference(
            document_id=self.doc_a,
            page_start=1,
            page_end=1,
            source_span="Some span",
            match_type=EvidenceMatchType.EXACT,
            validation_status=EvidenceValidationStatus.VALID,
        )
        claim = Claim.create(
            document_id=self.doc_a,
            claim_text="Party claim",
            claim_type=ClaimType.PARTY,
            evidence=ref,
        )
        report = DocumentEvidenceReport(
            document_id=self.doc_a,
            claims=[claim],
            coverage=EvidenceCoverage.calculate([claim]),
        )
        self.repo.save_evidence_report(report)

        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s;", (self.doc_a,))

        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(
                    (
                        "SELECT COUNT(*) as cnt FROM document_evidence_records "
                        "WHERE document_id = %s;"
                    ),
                    (self.doc_a,),
                )
                cnt = cur.fetchone()[0]
                assert cnt == 0
