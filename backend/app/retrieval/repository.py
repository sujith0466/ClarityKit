import math
from abc import ABC, abstractmethod
from threading import Lock

from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.retrieval.models import RetrievalChunk, RetrievalResult


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))

    if norm1 <= 1e-9 or norm2 <= 1e-9:
        return 0.0

    return dot / (norm1 * norm2)


class ChunkRepository(ABC):
    """Abstract interface for managing and searching retrieval chunks."""

    @abstractmethod
    def save_chunks(
        self, document_id: str, chunks: list[RetrievalChunk]
    ) -> list[RetrievalChunk]:
        """Save chunks for a document, replacing previous records idempotently."""
        pass

    @abstractmethod
    def get_chunks_by_document(self, document_id: str) -> list[RetrievalChunk]:
        """Retrieve all chunks for a document ordered by chunk_index."""
        pass

    @abstractmethod
    def delete_chunks_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        pass

    @abstractmethod
    def count_chunks(self, document_id: str) -> int:
        """Return the count of chunks for a document."""
        pass

    @abstractmethod
    def search_similar_chunks(
        self,
        user_id: str,
        query_vector: list[float],
        top_k: int = 5,
        document_id: str | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievalResult]:
        """Search vector chunks strictly within the authenticated user's documents."""
        pass


class InMemoryVectorChunkRepository(ChunkRepository):
    """Thread-safe in-memory vector chunk repository with strict tenant isolation."""

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
    ) -> None:
        self._lock = Lock()
        self._doc_repo = document_repository or in_memory_document_repository
        # Key: (document_id, chunk_index) -> RetrievalChunk
        self._chunks: dict[tuple[str, int], RetrievalChunk] = {}

    def save_chunks(
        self, document_id: str, chunks: list[RetrievalChunk]
    ) -> list[RetrievalChunk]:
        with self._lock:
            # Atomic replacement of document chunks
            keys_to_remove = [k for k in self._chunks if k[0] == document_id]
            for k in keys_to_remove:
                del self._chunks[k]

            for chunk in chunks:
                self._chunks[(document_id, chunk.chunk_index)] = chunk

            return sorted(
                [c for k, c in self._chunks.items() if k[0] == document_id],
                key=lambda c: c.chunk_index,
            )

    def get_chunks_by_document(self, document_id: str) -> list[RetrievalChunk]:
        with self._lock:
            return sorted(
                [c for k, c in self._chunks.items() if k[0] == document_id],
                key=lambda c: c.chunk_index,
            )

    def delete_chunks_by_document(self, document_id: str) -> int:
        with self._lock:
            keys_to_remove = [k for k in self._chunks if k[0] == document_id]
            for k in keys_to_remove:
                del self._chunks[k]
            return len(keys_to_remove)

    def count_chunks(self, document_id: str) -> int:
        with self._lock:
            return sum(1 for k in self._chunks if k[0] == document_id)

    def search_similar_chunks(
        self,
        user_id: str,
        query_vector: list[float],
        top_k: int = 5,
        document_id: str | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievalResult]:
        """Execute vector similarity search strictly within user's owned documents.

        Enforces tenant isolation directly in query evaluation.
        """
        with self._lock:
            # 1. Determine allowed document IDs owned by user_id
            if document_id:
                doc = self._doc_repo.get_by_id(document_id)
                if (
                    doc is None
                    or doc.user_id != user_id
                    or doc.status == DocumentStatus.DELETED
                ):
                    return []
                allowed_doc_ids = {document_id}
            else:
                user_docs = self._doc_repo.list_by_user(user_id, include_deleted=False)
                allowed_doc_ids = {
                    d.id for d in user_docs if d.status != DocumentStatus.DELETED
                }

            if not allowed_doc_ids:
                return []

            # 2. Score candidate chunks belonging exclusively to allowed documents
            candidates: list[tuple[float, RetrievalChunk]] = []
            for (doc_id, _), chunk in self._chunks.items():
                if doc_id not in allowed_doc_ids:
                    continue
                if chunk.embedding is None:
                    continue

                sim = cosine_similarity(query_vector, chunk.embedding)
                if min_similarity is not None and sim < min_similarity:
                    continue

                candidates.append((sim, chunk))

            # 3. Sort by similarity descending
            candidates.sort(key=lambda x: x[0], reverse=True)
            top_candidates = candidates[:top_k]

            # 4. Map to safe RetrievalResult objects
            results: list[RetrievalResult] = []
            for sim, chunk in top_candidates:
                word_count = len(chunk.text.split())
                results.append(
                    RetrievalResult(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        similarity=sim,
                        char_count=chunk.char_count,
                        word_count=word_count,
                    )
                )

            return results


class PgVectorChunkRepository(ChunkRepository):
    """PostgreSQL + pgvector chunk repository with tenant isolation in SQL."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _get_conn(self):  # type: ignore[no-untyped-def]
        import psycopg2
        from pgvector.psycopg2 import register_vector

        conn = psycopg2.connect(self._database_url)
        register_vector(conn)
        return conn

    def save_chunks(
        self, document_id: str, chunks: list[RetrievalChunk]
    ) -> list[RetrievalChunk]:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    # Atomic replacement
                    cur.execute(
                        "DELETE FROM retrieval_chunks WHERE document_id = %s;",
                        (document_id,),
                    )
                    for chunk in chunks:
                        cur.execute(
                            """
                            INSERT INTO retrieval_chunks (
                                id, document_id, chunk_index, text,
                                page_start, page_end, char_count,
                                token_count_est, content_hash, embedding,
                                created_at, updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                NOW(), NOW()
                            );
                            """,
                            (
                                chunk.id,
                                chunk.document_id,
                                chunk.chunk_index,
                                chunk.text,
                                chunk.page_start,
                                chunk.page_end,
                                chunk.char_count,
                                chunk.token_count_est,
                                chunk.content_hash,
                                chunk.embedding,
                            ),
                        )
            return self.get_chunks_by_document(document_id)
        finally:
            conn.close()

    def get_chunks_by_document(self, document_id: str) -> list[RetrievalChunk]:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, document_id, chunk_index, text, page_start,
                           page_end, char_count, token_count_est,
                           content_hash, embedding, created_at, updated_at
                    FROM retrieval_chunks
                    WHERE document_id = %s
                    ORDER BY chunk_index ASC;
                    """,
                    (document_id,),
                )
                rows = cur.fetchall()
                results: list[RetrievalChunk] = []
                for r in rows:
                    if r[9] is not None:
                        emb = r[9].to_list() if hasattr(r[9], "to_list") else list(r[9])
                    else:
                        emb = None
                    results.append(
                        RetrievalChunk(
                            id=str(r[0]),
                            document_id=str(r[1]),
                            chunk_index=int(r[2]),
                            text=str(r[3]),
                            page_start=int(r[4]),
                            page_end=int(r[5]),
                            source_page_ids=[],
                            char_count=int(r[6]),
                            token_count_est=int(r[7]),
                            content_hash=str(r[8]),
                            embedding=emb,
                            created_at=str(r[10]),
                            updated_at=str(r[11]),
                        )
                    )
                return results
        finally:
            conn.close()

    def delete_chunks_by_document(self, document_id: str) -> int:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM retrieval_chunks WHERE document_id = %s;",
                        (document_id,),
                    )
                    return int(cur.rowcount)
        finally:
            conn.close()

    def count_chunks(self, document_id: str) -> int:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM retrieval_chunks WHERE document_id = %s;",
                    (document_id,),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
        finally:
            conn.close()

    def search_similar_chunks(
        self,
        user_id: str,
        query_vector: list[float],
        top_k: int = 5,
        document_id: str | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievalResult]:
        """Execute pgvector similarity search strictly in SQL query."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        rc.id,
                        rc.document_id,
                        rc.chunk_index,
                        rc.text,
                        rc.page_start,
                        rc.page_end,
                        rc.char_count,
                        1.0 - (rc.embedding <=> %s::vector) AS similarity
                    FROM retrieval_chunks rc
                    JOIN documents d ON d.id = rc.document_id
                    WHERE d.user_id = %s AND d.status != 'deleted'
                      AND (%s::uuid IS NULL OR rc.document_id = %s::uuid)
                      AND rc.embedding IS NOT NULL
                    ORDER BY rc.embedding <=> %s::vector ASC
                    LIMIT %s;
                    """,
                    (
                        query_vector,
                        user_id,
                        document_id,
                        document_id,
                        query_vector,
                        top_k,
                    ),
                )
                rows = cur.fetchall()
                results: list[RetrievalResult] = []
                for r in rows:
                    sim = float(r[7])
                    if min_similarity is not None and sim < min_similarity:
                        continue
                    text = str(r[3])
                    results.append(
                        RetrievalResult(
                            chunk_id=str(r[0]),
                            document_id=str(r[1]),
                            chunk_index=int(r[2]),
                            text=text,
                            page_start=int(r[4]),
                            page_end=int(r[5]),
                            similarity=sim,
                            char_count=int(r[6]),
                            word_count=len(text.split()),
                        )
                    )
                return results
        finally:
            conn.close()


# Global singleton repository instance for in-memory runtime
in_memory_chunk_repository = InMemoryVectorChunkRepository()


def get_chunk_repository() -> ChunkRepository:
    """Return active ChunkRepository (PgVectorChunkRepository if configured)."""
    from app.config import Config

    if Config.DATABASE_URL:
        return PgVectorChunkRepository(Config.DATABASE_URL)
    return in_memory_chunk_repository
