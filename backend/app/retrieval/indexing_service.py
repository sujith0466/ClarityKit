import logging
from typing import Any

from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.processing.repository import PageRepository, in_memory_page_repository
from app.retrieval.chunker import DocumentChunker
from app.retrieval.embeddings import (
    CachedEmbeddingProvider,
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
)
from app.retrieval.models import IndexingError, RetrievalChunk
from app.retrieval.repository import ChunkRepository, get_chunk_repository

logger = logging.getLogger(__name__)


class IndexingService:
    """Orchestrates chunking, embedding generation, and vector persistence."""

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        page_repository: PageRepository | None = None,
        chunk_repository: ChunkRepository | None = None,
        chunker: DocumentChunker | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self._doc_repo = document_repository or in_memory_document_repository
        self._page_repo = page_repository or in_memory_page_repository
        self._chunk_repo = chunk_repository or get_chunk_repository()
        self._chunker = chunker or DocumentChunker()
        self._embedding_provider = embedding_provider or CachedEmbeddingProvider(
            DeterministicEmbeddingProvider()
        )

    def index_document(self, user_id: str, document_id: str) -> list[RetrievalChunk]:
        """Index a processed document: chunk pages, compute embeddings, persist vectors.

        Idempotent: Re-indexing atomically replaces previous chunks.
        """
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return []

        if doc.status != DocumentStatus.READY:
            raise IndexingError(
                f"Document '{document_id}' cannot be indexed in status '{doc.status}'."
            )

        # 1. Retrieve processed pages
        pages = self._page_repo.get_pages_by_document(document_id)
        if not pages:
            logger.info(f"Document {document_id} has 0 pages; creating 0 chunks.")
            self._chunk_repo.save_chunks(document_id, [])
            return []

        # 2. Deterministic chunking
        try:
            chunks = self._chunker.chunk_document(document_id, pages)
        except Exception as e:
            logger.error(f"Chunking failed for doc {document_id}: {e}", exc_info=True)
            raise IndexingError(f"Chunking failed: {e}") from e

        if not chunks:
            self._chunk_repo.save_chunks(document_id, [])
            return []

        # 3. Batch vector embedding generation
        try:
            chunk_texts = [c.text for c in chunks]
            embeddings = self._embedding_provider.embed_documents(chunk_texts)

            # Assign embeddings to chunks
            for i, chunk in enumerate(chunks):
                chunk.embedding = embeddings[i]
        except Exception as e:
            logger.error(
                f"Embedding generation failed for doc {document_id}: {e}",
                exc_info=True,
            )
            raise IndexingError(f"Vector embedding generation failed: {e}") from e

        # 4. Atomic vector persistence
        try:
            saved_chunks = self._chunk_repo.save_chunks(document_id, chunks)
            return saved_chunks
        except Exception as e:
            logger.error(
                f"Chunk persistence failed for doc {document_id}: {e}",
                exc_info=True,
            )
            raise IndexingError(f"Vector chunk persistence failed: {e}") from e

    def get_document_chunks(
        self, user_id: str, document_id: str
    ) -> list[RetrievalChunk] | None:
        """Retrieve all stored chunks for a document owned by the user."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return None

        return self._chunk_repo.get_chunks_by_document(document_id)

    def get_indexing_summary(
        self, user_id: str, document_id: str
    ) -> dict[str, Any] | None:
        """Retrieve indexing metadata and statistics for a document."""
        doc = self._doc_repo.get_by_id(document_id)
        if (
            doc is None
            or doc.user_id != user_id
            or doc.status == DocumentStatus.DELETED
        ):
            return None

        chunks = self._chunk_repo.get_chunks_by_document(document_id)
        total_tokens = sum(c.token_count_est for c in chunks)

        return {
            "document_id": doc.id,
            "status": "indexed" if chunks else "not_indexed",
            "chunk_count": len(chunks),
            "estimated_token_count": total_tokens,
            "embedding_dimensions": self._embedding_provider.dimensions,
            "embedding_model": self._embedding_provider.model_name,
        }


# Global singleton indexing service
default_indexing_service = IndexingService()
