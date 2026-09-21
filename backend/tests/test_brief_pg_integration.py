"""PostgreSQL integration tests for Lawyer Preparation Briefs."""

import os
import uuid
from collections.abc import Generator

import pytest

from app.brief.models import (
    BriefItem,
    BriefQuestion,
    BriefSection,
    BriefSourceType,
    LawyerPreparationBrief,
)
from app.brief.repository import PostgresBriefRepository
from app.database import get_db_connection, run_migrations
from app.trust.models import SafetyStatus, TrustTier

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="Live PostgreSQL DATABASE_URL not set")
class TestPgBriefRepositoryIntegration:
    @pytest.fixture(autouse=True)
    def setup_database(self) -> Generator[None, None, None]:
        assert DATABASE_URL is not None
        run_migrations(DATABASE_URL)
        self.repo = PostgresBriefRepository(DATABASE_URL)
        self.conn = get_db_connection(DATABASE_URL)

        self.user_id = str(uuid.uuid4())
        self.doc_id = str(uuid.uuid4())

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, password_hash, name)
                VALUES (%s, %s, %s, %s);
                """,
                (
                    self.user_id,
                    f"brief_{self.user_id[:8]}@example.com",
                    "dummyhash",
                    "Brief Test User",
                ),
            )
            cur.execute(
                """
                INSERT INTO documents (
                    id, user_id, filename, storage_path, size_bytes,
                    content_type, sha256_hash, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    self.doc_id,
                    self.user_id,
                    "pg_brief_test.pdf",
                    "/tmp/dummy",
                    1024,
                    "application/pdf",
                    "sha-pg-brief",
                    "READY",
                ),
            )
            self.conn.commit()

        yield

        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s;", (self.doc_id,))
            cur.execute("DELETE FROM users WHERE id = %s;", (self.user_id,))
            self.conn.commit()
        self.conn.close()

    def test_save_and_retrieve_brief(self) -> None:
        brief_id = str(uuid.uuid4())
        item = BriefItem(
            id=str(uuid.uuid4()),
            text="Landlord Corp",
            source_type=BriefSourceType.PARTY,
            trust_tier=TrustTier.DOCUMENT_FACT,
            safety_status=SafetyStatus.SAFE,
            page_start=1,
            page_end=1,
        )
        section = BriefSection(
            section_key="parties",
            title="Identified Parties",
            description="Signatories",
            items=[item],
        )
        brief = LawyerPreparationBrief(
            id=brief_id,
            document_id=self.doc_id,
            title="PG Integration Brief",
            situation_summary="Situation summary in PG",
            sections={"parties": section},
            questions_for_lawyer=[
                BriefQuestion(
                    question="What is the governing jurisdiction standard?",
                    category="jurisdiction",
                )
            ],
            facts_to_confirm=["Confirm entity registration"],
            documents_to_bring=["Executed PDF"],
            open_questions=["Is there an addendum?"],
            completeness_score=0.9,
        )

        self.repo.save_brief(brief, self.user_id)

        fetched = self.repo.get_brief_by_id(brief_id, self.user_id)
        assert fetched is not None
        assert fetched.id == brief_id
        assert fetched.document_id == self.doc_id
        assert fetched.title == "PG Integration Brief"
        assert len(fetched.questions_for_lawyer) == 1
        assert fetched.completeness_score == 0.9

        by_doc = self.repo.get_latest_brief_by_document(self.doc_id, self.user_id)
        assert by_doc is not None
        assert by_doc.id == brief_id

        deleted = self.repo.delete_brief(brief_id, self.user_id)
        assert deleted is True
        assert self.repo.get_brief_by_id(brief_id, self.user_id) is None
