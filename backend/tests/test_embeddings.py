import math

from app.retrieval.embeddings import (
    CachedEmbeddingProvider,
    DeterministicEmbeddingProvider,
)


def test_deterministic_embedding_provider_properties() -> None:
    """Test dimension, normalization, and model name properties."""
    provider = DeterministicEmbeddingProvider(dimensions=384)

    assert provider.dimensions == 384
    assert provider.model_name == "deterministic-minilm-384"

    # Query embedding
    q_vec = provider.embed_query("breach of contract damages")
    assert len(q_vec) == 384
    # Check L2 unit norm
    norm = math.sqrt(sum(v * v for v in q_vec))
    assert abs(norm - 1.0) < 1e-4

    # Batch document embeddings
    docs = [
        "Confidentiality non-disclosure clause",
        "Termination and notice requirements",
    ]
    doc_vecs = provider.embed_documents(docs)
    assert len(doc_vecs) == 2
    assert len(doc_vecs[0]) == 384
    assert len(doc_vecs[1]) == 384


def test_deterministic_embeddings_repeatability() -> None:
    """Test that identical text yields exact same float vector."""
    provider = DeterministicEmbeddingProvider()
    text = "Governing law shall be the State of Delaware."

    v1 = provider.embed_query(text)
    v2 = provider.embed_query(text)

    assert v1 == v2


def test_cached_embedding_provider_caching() -> None:
    """Test that CachedEmbeddingProvider reuses cached results without recomputation."""
    base_provider = DeterministicEmbeddingProvider()
    cached = CachedEmbeddingProvider(base_provider)

    assert cached.cache_size == 0

    text1 = "Arbitration clause and dispute resolution mechanism."
    text2 = "Severability of invalid contract terms."

    # First computation: cache missed
    _ = cached.embed_documents([text1, text2])
    assert cached.cache_size == 2

    # Second computation: cache hit
    res2 = cached.embed_documents([text1, text2])
    assert len(res2) == 2
    assert cached.cache_size == 2

    # Query caching
    _ = cached.embed_query(text1)
    assert cached.cache_size == 2

    cached.clear_cache()
    assert cached.cache_size == 0
