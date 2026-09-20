import os
import uuid
from collections.abc import Generator

import pytest

from app.database import get_db_connection, run_migrations
from app.evidence.models import (
    ClaimType,
    EvidenceMatchType,
    EvidenceReference,
    EvidenceValidationStatus,
)
from app.trust.models import (
    AssessedClaim,
    SafetyStatus,
    TrustAssessment,
    TrustTier,
)
from app.trust.repository import PgTrustRepository

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="Live PostgreSQL DATABASE_URL not set")
class TestPgTrustRepositoryIntegration:
    @pytest.fixture(autouse=True)
    def setup_database(self) -> Generator[None, None, None]:
        assert DATABASE_URL is not None
        run_migrations(DATABASE_URL)
        self.repo = PgTrustRepository(DATABASE_URL)
        self.conn = get_db_connection(DATABASE_URL)

        self.user_id = str(uuid.uuid4())
        self.doc_id = str(uuid.uuid4())

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, password_hash, name)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    self.user_id,
                    f"user_{self.user_id[:8]}@example.com",
                    "dummyhash",
                    "Test User",
                ),
            )
            cur.execute(
                """
                INSERT INTO documents (
                    id, user_id, filename, storage_path, size_bytes,
                    content_type, sha256_hash, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    self.doc_id,
                    self.user_id,
                    "contract.pdf",
                    f"/storage/{self.doc_id}",
                    2048,
                    "application/pdf",
                    "dummyhash",
                    "ready",
                ),
            )
        self.conn.commit()

        yield

        # Cleanup
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (self.doc_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (self.user_id,))
        self.conn.commit()
        self.conn.close()

    def test_save_and_retrieve_trust_assessments(self) -> None:
        cid = str(uuid.uuid4())
        assessment = TrustAssessment(
            claim_id=cid,
            trust_tier=TrustTier.DOCUMENT_FACT,
            safety_status=SafetyStatus.SAFE,
            evidence_required=True,
            evidence_valid=True,
            professional_review_required=False,
            limitations=[],
            reasoning_summary="Supported fact",
        )
        ev = EvidenceReference(
            document_id=self.doc_id,
            page_start=1,
            page_end=1,
            source_span="Valid source span",
            match_type=EvidenceMatchType.EXACT,
            validation_status=EvidenceValidationStatus.VALID,
        )
        item = AssessedClaim(
            id=str(uuid.uuid4()),
            document_id=self.doc_id,
            claim_text="Verified contract fact",
            claim_type=ClaimType.OBLIGATION,
            trust_assessment=assessment,
            evidence=ev,
        )

        self.repo.save_assessments(self.doc_id, [item])
        retrieved = self.repo.get_by_document(self.doc_id, self.user_id)
        assert len(retrieved) == 1
        assert retrieved[0].claim_text == "Verified contract fact"
        assert retrieved[0].trust_assessment.trust_tier == TrustTier.DOCUMENT_FACT
        assert retrieved[0].trust_assessment.safety_status == SafetyStatus.SAFE

    def test_tenant_isolation_on_trust_retrieval(self) -> None:
        other_user = str(uuid.uuid4())
        retrieved = self.repo.get_by_document(self.doc_id, other_user)
        assert len(retrieved) == 0
