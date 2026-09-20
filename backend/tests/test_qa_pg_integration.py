import os
import uuid
from collections.abc import Generator

import pytest

from app.database import get_db_connection, run_migrations
from app.qa.models import AnswerClaim, QAMessage, QASession
from app.qa.repository import PostgresQARepository
from app.trust.models import SafetyStatus, TrustTier

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="Live PostgreSQL DATABASE_URL not set")
class TestPgQARepositoryIntegration:
    @pytest.fixture(autouse=True)
    def setup_database(self) -> Generator[None, None, None]:
        assert DATABASE_URL is not None
        run_migrations(DATABASE_URL)
        self.repo = PostgresQARepository(DATABASE_URL)
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
                    f"qa_{self.user_id[:8]}@example.com",
                    "dummyhash",
                    "QA Test User",
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
                    "pg_qa_test.pdf",
                    "/tmp/dummy",
                    1024,
                    "application/pdf",
                    "sha-pg-qa",
                    "READY",
                ),
            )
            self.conn.commit()

        yield

        # Cleanup
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s;", (self.doc_id,))
                cur.execute("DELETE FROM users WHERE id = %s;", (self.user_id,))
                self.conn.commit()
        except Exception:
            pass
        finally:
            self.conn.close()

    def test_session_and_message_lifecycle_postgres(self) -> None:
        # 1. Create session
        session = QASession(
            id=str(uuid.uuid4()),
            document_id=self.doc_id,
            title="Live PG QA Session",
        )
        created_session = self.repo.create_session(session, self.user_id)
        assert created_session.id == session.id
        assert created_session.title == "Live PG QA Session"

        # 2. Save QAMessage
        msg = QAMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            document_id=self.doc_id,
            question_text="What is the notice period?",
            answer_text="Notice period is 30 days.",
            trust_tier=TrustTier.DOCUMENT_FACT,
            safety_status=SafetyStatus.SAFE,
            evidence_coverage=1.0,
            is_grounded=True,
            claims=[
                AnswerClaim(
                    id=str(uuid.uuid4()),
                    claim_text="30 days notice",
                    claim_type="document_fact",
                    trust_tier=TrustTier.DOCUMENT_FACT,
                )
            ],
            evidence_references=[
                {
                    "claim_id": "c-1",
                    "page_start": 1,
                    "page_end": 1,
                    "source_span": "30 days",
                }
            ],
        )
        saved_msg = self.repo.save_message(msg, self.user_id)
        assert saved_msg.id == msg.id

        # 3. Retrieve messages
        messages = self.repo.get_messages_by_session(session.id, self.user_id)
        assert len(messages) == 1
        assert messages[0].question_text == "What is the notice period?"
        assert messages[0].trust_tier == TrustTier.DOCUMENT_FACT
        assert messages[0].is_grounded is True

        # 4. Retrieve single message by ID
        single_msg = self.repo.get_message_by_id(msg.id, self.user_id)
        assert single_msg is not None
        assert single_msg.id == msg.id

        # 5. List sessions
        sessions = self.repo.list_sessions_by_document(self.doc_id, self.user_id)
        assert len(sessions) >= 1

        # 6. Delete session cascades messages
        deleted = self.repo.delete_session(session.id, self.user_id)
        assert deleted is True
        assert len(self.repo.get_messages_by_session(session.id, self.user_id)) == 0
