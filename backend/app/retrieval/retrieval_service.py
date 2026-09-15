import logging
from typing import Any

from app.documents.models import DocumentStatus
from app.documents.repository import DocumentRepository, in_memory_document_repository
from app.retrieval.embeddings import (
    CachedEmbeddingProvider,
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
)
from app.retrieval.models import (
    InvalidQueryError,
    RetrievalError,
    RetrievalResult,
)
from app.retrieval.repository import ChunkRepository, get_chunk_repository

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 1000
MAX_TOP_K = 50
DEFAULT_TOP_K = 5


class RetrievalService:
    """Provides secure, tenant-isolated vector semantic search."""

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        chunk_repository: ChunkRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        max_query_length: int = MAX_QUERY_LENGTH,
        max_top_k: int = MAX_TOP_K,
        default_top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self._doc_repo = document_repository or in_memory_document_repository
        self._chunk_repo = chunk_repository or get_chunk_repository()
        self._embedding_provider = embedding_provider or CachedEmbeddingProvider(
            DeterministicEmbeddingProvider()
        )
        self._max_query_length = max_query_length
        self._max_top_k = max_top_k
        self._default_top_k = default_top_k

    def retrieve(
        self,
        user_id: str,
        query: str,
        document_id: str | None = None,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievalResult]:
        """Execute semantic search strictly within caller's authorized document space.

        Enforces tenant isolation, input validation, and bounded top-k retrieval.
        """
        # 1. Validate query string
        clean_query = (query or "").strip()
        if not clean_query:
            raise InvalidQueryError("Search query cannot be empty.")

        if len(clean_query) > self._max_query_length:
            raise InvalidQueryError(
                f"Query length ({len(clean_query)} chars) exceeds maximum "
                f"allowed limit of {self._max_query_length} characters."
            )

        # 2. Validate top_k parameter
        k = top_k if top_k is not None else self._default_top_k
        if k < 1:
            raise InvalidQueryError("top_k must be an integer >= 1.")
        if k > self._max_top_k:
            raise InvalidQueryError(
                f"top_k ({k}) exceeds maximum allowed limit of {self._max_top_k}."
            )

        # 3. Validate document_id ownership if scoped
        if document_id:
            doc = self._doc_repo.get_by_id(document_id)
            if (
                doc is None
                or doc.user_id != user_id
                or doc.status == DocumentStatus.DELETED
            ):
                # Document not found or not owned by user: return empty results
                return []

        # 4. Generate query vector embedding
        try:
            query_vector = self._embedding_provider.embed_query(clean_query)
        except Exception as e:
            logger.error(f"Query embedding generation failed: {e}", exc_info=True)
            raise RetrievalError(f"Query embedding failed: {e}") from e

        # 5. Execute vector search with query-boundary ownership filtering
        try:
            results = self._chunk_repo.search_similar_chunks(
                user_id=user_id,
                query_vector=query_vector,
                top_k=k,
                document_id=document_id,
                min_similarity=min_similarity,
            )
            return results
        except Exception as e:
            logger.error(
                f"Vector retrieval query failed for user {user_id}: {e}",
                exc_info=True,
            )
            raise RetrievalError(f"Vector retrieval failed: {e}") from e

    def get_service_metadata(self) -> dict[str, Any]:
        """Return public service parameters and bounds."""
        return {
            "embedding_dimensions": self._embedding_provider.dimensions,
            "embedding_model": self._embedding_provider.model_name,
            "max_query_length": self._max_query_length,
            "max_top_k": self._max_top_k,
            "default_top_k": self._default_top_k,
            "similarity_metric": "cosine",
        }


# Global singleton retrieval service
default_retrieval_service = RetrievalService()
