"""ClarityKit Phase 5: Chunking, Indexing & Retrieval Package."""

from app.retrieval.chunker import ChunkingConfig, DocumentChunker
from app.retrieval.embeddings import (
    CachedEmbeddingProvider,
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
)
from app.retrieval.indexing_service import (
    IndexingService,
    default_indexing_service,
)
from app.retrieval.models import (
    EmbeddingError,
    IndexingError,
    InvalidQueryError,
    RetrievalChunk,
    RetrievalError,
    RetrievalResult,
)
from app.retrieval.repository import (
    ChunkRepository,
    InMemoryVectorChunkRepository,
    in_memory_chunk_repository,
)
from app.retrieval.retrieval_service import (
    RetrievalService,
    default_retrieval_service,
)

__all__ = [
    "ChunkRepository",
    "ChunkingConfig",
    "DocumentChunker",
    "EmbeddingError",
    "EmbeddingProvider",
    "DeterministicEmbeddingProvider",
    "CachedEmbeddingProvider",
    "IndexingError",
    "IndexingService",
    "InMemoryVectorChunkRepository",
    "InvalidQueryError",
    "RetrievalChunk",
    "RetrievalError",
    "RetrievalResult",
    "RetrievalService",
    "default_indexing_service",
    "default_retrieval_service",
    "in_memory_chunk_repository",
]
