import hashlib
import math
import struct
from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.retrieval.models import EmbeddingError

DEFAULT_EMBEDDING_DIMENSIONS = 384
DEFAULT_EMBEDDING_MODEL = "deterministic-minilm-384"


class EmbeddingProvider(ABC):
    """Abstract base provider for vector embeddings."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the vector dimensionality of embeddings produced by this provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        pass

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Compute normalized vector embeddings for a batch of texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Compute normalized vector embedding for a single search query."""
        pass


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Deterministic, zero-dependency embedding provider for local dev & testing.

    Generates normalized 384-dimensional dense vectors derived from term frequencies
    and deterministic hashing with cosine-distance properties.
    """

    def __init__(
        self,
        dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        self._dimensions = dimensions
        self._model_name = model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            return [self._generate_vector(t) for t in texts]
        except Exception as e:
            raise EmbeddingError(f"Failed to generate document embeddings: {e}") from e

    def embed_query(self, text: str) -> list[float]:
        try:
            return self._generate_vector(text)
        except Exception as e:
            raise EmbeddingError(f"Failed to generate query embedding: {e}") from e

    def _generate_vector(self, text: str) -> list[float]:
        """Generate a deterministic unit-normalized float vector."""
        if not text.strip():
            return [0.0] * self._dimensions

        # Initialize dense vector
        vec = [0.0] * self._dimensions
        words = text.lower().split()

        for word in words:
            # Hash word to determine dimension slots and weights
            h = hashlib.sha256(word.encode("utf-8")).digest()
            # Unpack 8 32-bit ints from sha256
            slots = struct.unpack(">8I", h)
            for i, slot in enumerate(slots):
                idx = slot % self._dimensions
                val = ((slot >> 16) & 0xFF) / 255.0 - 0.5
                vec[idx] += val * (1.0 / (i + 1))

        # Overall text seed contribution
        text_hash = hashlib.sha256(text.strip().encode("utf-8")).digest()
        for i in range(min(self._dimensions, 32)):
            vec[i] += (text_hash[i % 32] / 255.0 - 0.5) * 0.2

        # L2-normalize vector to unit length
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-9:
            vec = [v / norm for v in vec]
        else:
            vec = [0.0] * self._dimensions
            vec[0] = 1.0

        return vec


class CachedEmbeddingProvider(EmbeddingProvider):
    """Wrapper that caches vector embeddings by text content hash and model name."""

    def __init__(
        self,
        inner_provider: EmbeddingProvider,
        max_cache_size: int = 50000,
    ) -> None:
        self._inner = inner_provider
        self._max_cache_size = max_cache_size
        # Key: (content_hash, model_name) -> list[float]
        self._cache: dict[str, list[float]] = {}

    @property
    def dimensions(self) -> int:
        return self._inner.dimensions

    @property
    def model_name(self) -> str:
        return self._inner.model_name

    def _make_cache_key(self, text: str) -> str:
        clean = text.strip()
        h = hashlib.sha256(f"{clean}:{self.model_name}".encode()).hexdigest()
        return h

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        results: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for i, text in enumerate(texts):
            key = self._make_cache_key(text)
            if key in self._cache:
                results[i] = self._cache[key]
            else:
                missing_indices.append(i)
                missing_texts.append(text)

        if missing_texts:
            new_embeddings = self._inner.embed_documents(missing_texts)
            for idx, orig_i in enumerate(missing_indices):
                emb = new_embeddings[idx]
                results[orig_i] = emb
                key = self._make_cache_key(texts[orig_i])
                if len(self._cache) < self._max_cache_size:
                    self._cache[key] = emb

        return [r for r in results if r is not None]

    def embed_query(self, text: str) -> list[float]:
        # Queries can also be cached
        key = self._make_cache_key(text)
        if key in self._cache:
            return self._cache[key]
        emb = self._inner.embed_query(text)
        if len(self._cache) < self._max_cache_size:
            self._cache[key] = emb
        return emb

    def clear_cache(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Return count of cached embeddings."""
        return len(self._cache)
