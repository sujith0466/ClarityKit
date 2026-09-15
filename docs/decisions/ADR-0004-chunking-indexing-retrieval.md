# ADR-0004: Document Chunking, Indexing & Tenant-Isolated Vector Retrieval

## Status
Accepted / Verified (Neon PostgreSQL + pgvector Live Integration Verified)

## Context
ClarityKit transforms complex legal documents into understandable, traceable, and actionable information. Following Phase 4 (Document Processing & OCR), uploaded documents are available as ordered, normalized `DocumentPage` entities (`document_id`, `page_number`, `text`, `extraction_method`).

To support later structured extraction (Phase 6), evidence grounding (Phase 7), and grounded Q&A (Phase 10), ClarityKit requires a deterministic retrieval foundation that indexes source text into semantic chunks while maintaining source traceability back to specific pages and documents.

## Decision

### 1. No Orphan Chunks & Page Provenance
- Every chunk is strictly derived from verified `DocumentPage` records.
- Chunks retain explicit provenance: `document_id`, `chunk_index`, `page_start`, `page_end`, and `source_page_ids`.
- If a chunk spans across page boundaries (e.g., continuous contract clauses crossing from page 3 to page 4), `page_start = 3` and `page_end = 4` are preserved explicitly.

### 2. Deterministic Chunking Strategy
- **Text Splitting**: Natural legal boundary splitting (paragraphs and sentence breaks) rather than blind character slicing.
- **Chunk Configuration**:
  - `target_chunk_size`: 600 characters (~100-120 words)
  - `chunk_overlap`: 120 characters (~20-25 words)
  - `min_chunk_size`: 80 characters
- **Content Integrity**: Text is preserved verbatim from normalized source pages (no summarization, grammatical alterations, or legal interpretations).
- **Hashing**: Deterministic SHA-256 hashing (`content_hash`) per chunk.

### 3. Embedding Provider Abstraction & Caching
- Defined `EmbeddingProvider` interface (`embed_documents`, `embed_query`, `dimensions`, `model_name`).
- Standard vector dimension: 384 dimensions.
- **Development / Test Provider**: `DeterministicEmbeddingProvider` generates deterministic 384-dimensional unit vectors derived from term hashing and hypersphere projection. It is explicitly classified as a **TEST/DEVELOPMENT PROVIDER** (not a trained neural semantic model).
- **Embedding Cache**: Cached deterministically by `hash(chunk_text + ":" + model_name)` to avoid redundant recomputations.

### 4. Vector Storage & Database Strategy
- **Production Architecture**: PostgreSQL with `pgvector` extension.
  - Migration: `0002_retrieval_chunks_pgvector.sql`
  - Table: `retrieval_chunks`
  - Vector column: `embedding vector(384)`
  - Distance metric: Cosine distance (`<=>`)
  - Indexing: HNSW with `vector_cosine_ops` (`m = 16`, `ef_construction = 64`)
  - Live implementation: `PgVectorChunkRepository` verified against Neon PostgreSQL.
- **In-Memory Fallback**: Thread-safe `InMemoryVectorChunkRepository` computing exact cosine similarity over normalized vector embeddings when `DATABASE_URL` is omitted.

### 5. Tenant Isolation at Query Boundary
- Security rule: Retrieval queries MUST filter by `user_id` at the database query boundary in SQL (`JOIN documents d ON d.id = rc.document_id WHERE d.user_id = %s`).
- Vector similarity search is executed strictly within the caller's authorized document partition.
- Cross-tenant documents are never scanned, ranked, or exposed, preventing cross-tenant leakage even if an unauthorized document has higher cosine similarity.
- Queries targeting non-owned document IDs return `404 Not Found` (never leaking existence).

### 6. Retrieval Ranking & Non-Claim of Legal Certainty
- Similarity scores represent mathematical vector proximity (`[0.0, 1.0]`), never legal correctness or legal confidence.

## Consequences
- Clean, decoupled retrieval substrate for Phase 6 (Structured Extraction) and Phase 7 (Evidence Engine).
- 100% provenance from retrieved chunk to document and page numbers.
- Absolute tenant isolation enforced at repository and database query boundaries.
- Live Neon PostgreSQL + pgvector integration verified in production runtime.
