-- ClarityKit Phase 5: Retrieval Chunks & pgvector Migration
-- Extension required: pgvector

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS retrieval_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    char_count INTEGER NOT NULL,
    token_count_est INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_document_chunk_index UNIQUE (document_id, chunk_index)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_retrieval_chunks_document_id 
    ON retrieval_chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_retrieval_chunks_content_hash 
    ON retrieval_chunks (content_hash);

-- HNSW Vector Cosine Index for Fast Approximate Nearest Neighbor Search
CREATE INDEX IF NOT EXISTS idx_retrieval_chunks_embedding_hnsw 
    ON retrieval_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);