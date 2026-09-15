import os
import uuid
from collections.abc import Generator

import pytest

from app.database import get_db_connection, run_migrations
from app.retrieval.embeddings import DeterministicEmbeddingProvider
from app.retrieval.models import RetrievalChunk
from app.retrieval.repository import PgVectorChunkRepository

# Skip if DATABASE_URL is not set
DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="Live PostgreSQL DATABASE_URL not set")
class TestNeonPgVectorLive:
    """T-080: Live Neon PostgreSQL + pgvector integration tests."""

    @pytest.fixture(autouse=True)
    def setup_live_db(self) -> Generator[None, None, None]:
        assert DATABASE_URL is not None
        # Ensure migrations are applied
        run_migrations(DATABASE_URL)
        self.repo = PgVectorChunkRepository(DATABASE_URL)
        self.embedder = DeterministicEmbeddingProvider(dimensions=384)
        self.conn = get_db_connection(DATABASE_URL)

        # Generate unique test fixture IDs
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
                        f"test_a_{self.user_a[:8]}@test.com",
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
                        f"test_b_{self.user_b[:8]}@test.com",
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
                        "doc_a.pdf",
                        "path/a",
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
                        "doc_b.pdf",
                        "path/b",
                        1024,
                        "application/pdf",
                        "hash_b",
                        "ready",
                    ),
                )

        yield

        # Teardown / Cleanup
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM retrieval_chunks WHERE document_id IN (%s, %s);",
                    (self.doc_a, self.doc_b),
                )
                cur.execute(
                    "DELETE FROM documents WHERE id IN (%s, %s);",
                    (self.doc_a, self.doc_b),
                )
                cur.execute(
                    "DELETE FROM users WHERE id IN (%s, %s);",
                    (self.user_a, self.user_b),
                )
        self.conn.close()

    def test_live_vector_persistence_and_dimensions(self) -> None:
        """Test persisting 384-dimensional vector in PostgreSQL catalog."""
        text = "Confidentiality and nondisclosure covenants under Delaware law."
        vec = self.embedder.embed_query(text)
        chunk_id = str(uuid.uuid4())

        chunk = RetrievalChunk(
            id=chunk_id,
            document_id=self.doc_a,
            chunk_index=0,
            text=text,
            page_start=1,
            page_end=1,
            source_page_ids=[],
            char_count=len(text),
            token_count_est=len(text.split()),
            content_hash="content_hash_1",
            embedding=vec,
        )

        saved = self.repo.save_chunks(self.doc_a, [chunk])
        assert len(saved) == 1
        assert saved[0].embedding is not None
        assert len(saved[0].embedding) == 384

        # Verify in raw SQL
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, embedding FROM retrieval_chunks WHERE id = %s;",
                (chunk_id,),
            )
            row = cur.fetchone()
            assert row is not None
            assert str(row[0]) == chunk_id

    def test_live_cosine_search_and_tenant_isolation(self) -> None:
        """Test that vector search strictly enforces tenant boundary in SQL."""
        text_a = "Standard office equipment maintenance agreement."
        text_b = "Proprietary deep neural network architecture trade secret patent."

        vec_a = self.embedder.embed_query(text_a)
        vec_b = self.embedder.embed_query(text_b)

        chunk_a = RetrievalChunk(
            id=str(uuid.uuid4()),
            document_id=self.doc_a,
            chunk_index=0,
            text=text_a,
            page_start=1,
            page_end=1,
            source_page_ids=[],
            char_count=len(text_a),
            token_count_est=len(text_a.split()),
            content_hash="hash_a",
            embedding=vec_a,
        )

        chunk_b = RetrievalChunk(
            id=str(uuid.uuid4()),
            document_id=self.doc_b,
            chunk_index=0,
            text=text_b,
            page_start=1,
            page_end=1,
            source_page_ids=[],
            char_count=len(text_b),
            token_count_est=len(text_b.split()),
            content_hash="hash_b",
            embedding=vec_b,
        )

        self.repo.save_chunks(self.doc_a, [chunk_a])
        self.repo.save_chunks(self.doc_b, [chunk_b])

        # User A searches for User B's exact trade secret keywords
        query_vec = self.embedder.embed_query(
            "deep neural network architecture trade secret"
        )
        results = self.repo.search_similar_chunks(
            user_id=self.user_a,
            query_vector=query_vec,
            top_k=5,
        )

        # Must return ONLY User A's chunks (no User B chunks)
        assert len(results) == 1
        assert results[0].document_id == self.doc_a
        assert "Standard office" in results[0].text
        assert "trade secret" not in results[0].text

    def test_live_reindexing_idempotency(self) -> None:
        """Test that re-indexing does not accumulate duplicate rows in Neon."""
        text = "Indemnity clause section 14."
        vec = self.embedder.embed_query(text)
        chunk = RetrievalChunk(
            id=str(uuid.uuid4()),
            document_id=self.doc_a,
            chunk_index=0,
            text=text,
            page_start=1,
            page_end=1,
            source_page_ids=[],
            char_count=len(text),
            token_count_est=len(text.split()),
            content_hash="hash_indemnity",
            embedding=vec,
        )

        self.repo.save_chunks(self.doc_a, [chunk])
        assert self.repo.count_chunks(self.doc_a) == 1

        # Re-index same document
        self.repo.save_chunks(self.doc_a, [chunk])
        assert self.repo.count_chunks(self.doc_a) == 1
