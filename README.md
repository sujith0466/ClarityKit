# ClarityKit

> An evidence-grounded legal document understanding and preparation platform that transforms complex legal documents into understandable, traceable, and actionable information without pretending to be a lawyer.

## Core Philosophy

**UNDERSTAND ? EXTRACT ? EVIDENCE ? ASSIST ? PREPARE**

---

## Current Status: Phase 5 — Chunking, Indexing & Retrieval

Phase 5 establishes the non-orphan retrieval chunking pipeline, embedding provider abstractions, vector storage with Neon PostgreSQL + pgvector, and multi-tenant vector retrieval:
- **Page-Aware Deterministic Chunking**: `DocumentChunker` produces traceable `RetrievalChunk` entities respecting paragraph/sentence boundaries, target size (600 chars), overlap (120 chars), and minimum chunk size (80 chars). Every chunk links directly to source `page_start`, `page_end`, `source_page_ids`, and SHA-256 `content_hash`.
- **Embedding Provider Abstraction**: Pluggable `EmbeddingProvider` interface with deterministic local unit-normalized vector generation (`DeterministicEmbeddingProvider` — classified as **Test/Development Provider**), caching (`CachedEmbeddingProvider`), and model metadata tracking.
- **Vector Storage & pgvector Integration**: PostgreSQL migration schema with pgvector `vector(384)` and HNSW cosine distance index (`vector_cosine_ops`), accompanied by `PgVectorChunkRepository` (verified against Neon PostgreSQL) and in-memory fallback repository (`InMemoryVectorChunkRepository`).
- **Idempotent Indexing Pipeline**: Synchronous document indexing (`IndexingService`) that validates `READY` processing status, chunks pages deterministically, generates embeddings, and replaces stale chunks atomically.
- **Multi-Tenant Vector Retrieval**: `RetrievalService` performs cosine similarity search filtered strictly by authenticated user ownership at the database query boundary in SQL (`JOIN documents d ON d.id = rc.document_id WHERE d.user_id = %s`), with query length validation (<= 1000 chars) and result caps (top_k <= 50).
- **Safe Mathematical Scoring**: Retrieval scores are explicitly documented and presented as mathematical vector cosine similarity only, avoiding misleading legal confidence claims.
- **Interactive Retrieval Inspection UI**: Document list indexing actions and semantic vector search query interface with ranked results, page provenance citations, and prominent legal disclaimer.

> [!NOTE]
> Phase 5 handles document chunking, indexing, and mathematical vector retrieval only. Generative LLM reasoning, clause classification, and legal Q&A will be introduced in subsequent phases according to the Master Plan.

---

## Security Architecture & API Endpoints

### Authentication Endpoints
- `POST /api/auth/register` — Register new user account (`email`, `password`, `name`).
- `POST /api/auth/login` — Authenticate user and receive JWT token (`email`, `password`).
- `POST /api/auth/logout` — Acknowledge session termination.
- `GET /api/auth/me` — Retrieve authenticated user profile (requires `Authorization: Bearer <token>`).

### Document Ingestion & Processing Endpoints
- `POST /api/documents` — Securely upload a PDF file (multipart/form-data with `file` field).
- `GET /api/documents` — List all active documents owned by the authenticated user.
- `GET /api/documents/<document_id>` — Retrieve document metadata (strictly verifies ownership, 404 for cross-tenant/missing).
- `DELETE /api/documents/<document_id>` — Delete document file, pages, and chunks (strictly verifies ownership, 404 for cross-tenant/missing).
- `POST /api/documents/<document_id>/process` — Trigger extraction & OCR processing on uploaded document.
- `GET /api/documents/<document_id>/pages` — Retrieve ordered extracted pages with text, method, and statistics.
- `GET /api/documents/<document_id>/processing` — Retrieve processing summary (status, page counts, OCR counts).

### Chunking, Indexing & Retrieval Endpoints
- `POST /api/documents/<document_id>/index` — Idempotently chunk, embed, and index a processed document.
- `GET /api/documents/<document_id>/chunks` — Retrieve all indexed chunks with page provenance for an owned document.
- `GET /api/documents/<document_id>/index` — Retrieve indexing metadata summary (chunk count, token estimate, model info).
- `POST /api/retrieval/search` — Perform vector cosine similarity search across owned documents (`query`, `top_k`, optional `document_ids`).

### Authorization & IDOR Policy
- **Unauthenticated access to protected resource** ? `HTTP 401 Unauthorized`
- **Authenticated access to nonexistent resource** ? `HTTP 404 Not Found`
- **Authenticated access to another user's resource** ? `HTTP 404 Not Found` (strict IDOR protection)
- **Authenticated access to owned resource** ? `HTTP 200 OK`

---

## Repository Structure

```text
claritykit/
+-- .github/
¦   +-- workflows/
¦       +-- ci.yml             # Unified GitHub Actions CI
+-- backend/
¦   +-- app/
¦   ¦   +-- auth/              # Authentication & Security core
¦   ¦   ¦   +-- context.py     # @require_auth & @require_ownership
¦   ¦   ¦   +-- models.py      # User entity
¦   ¦   ¦   +-- password.py    # Cryptographic password hashing
¦   ¦   ¦   +-- repository.py  # Pluggable user repository interface
¦   ¦   ¦   +-- service.py     # AuthService business logic
¦   ¦   ¦   +-- tokens.py      # JWT token generator & validator
¦   ¦   +-- documents/         # Document Ingestion core
¦   ¦   ¦   +-- models.py      # Document entity & metadata
¦   ¦   ¦   +-- repository.py  # Document repository interface & in-memory impl
¦   ¦   ¦   +-- service.py     # DocumentService & lifecycle management
¦   ¦   ¦   +-- storage.py     # FileStorageService with path traversal defense
¦   ¦   ¦   +-- validators.py  # PDF validation, magic bytes & size bounds
¦   ¦   +-- processing/        # Document Processing & OCR core
¦   ¦   ¦   +-- extractor.py   # PDF native text extraction & scanned detection
¦   ¦   ¦   +-- models.py      # DocumentPage entity & PageExtractionResult
¦   ¦   ¦   +-- normalizer.py  # Legal-safe text normalization
¦   ¦   ¦   +-- ocr.py         # OCRProvider interface & Tesseract integration
¦   ¦   ¦   +-- repository.py  # Page repository interface & in-memory impl
¦   ¦   ¦   +-- service.py     # DocumentProcessingService orchestration
¦   ¦   +-- retrieval/         # Chunking, Indexing & Retrieval core
¦   ¦   ¦   +-- chunker.py     # Deterministic page-aware document chunker
¦   ¦   ¦   +-- embeddings.py  # EmbeddingProvider interface & deterministic dev engine
¦   ¦   ¦   +-- indexing_service.py # Idempotent chunking & indexing coordinator
¦   ¦   ¦   +-- models.py      # RetrievalChunk, RetrievalResult, errors
¦   ¦   ¦   +-- repository.py  # Chunk repository (PgVector + InMemory) & similarity search
¦   ¦   ¦   +-- retrieval_service.py # Multi-tenant vector retrieval engine
¦   ¦   +-- routes/
¦   ¦   ¦   +-- __init__.py
¦   ¦   ¦   +-- auth.py        # /api/auth routes
¦   ¦   ¦   +-- documents.py   # /api/documents upload & metadata routes
¦   ¦   ¦   +-- health.py      # Health smoke endpoint (/api/health)
¦   ¦   ¦   +-- processing.py  # /api/documents/<id>/process & pages routes
¦   ¦   ¦   +-- retrieval.py   # /api/documents/<id>/index & /api/retrieval/search
¦   ¦   +-- __init__.py        # Flask application factory
¦   ¦   +-- config.py          # Security & environment configuration
¦   ¦   +-- database.py        # Database connection & migration runner
¦   ¦   +-- errors.py          # Standard JSON error handlers
¦   +-- migrations/            # SQL migration scripts (PostgreSQL + pgvector)
¦   ¦   +-- 0001_initial_schema.sql
¦   ¦   +-- 0002_retrieval_chunks_pgvector.sql
¦   +-- tests/
¦   ¦   +-- conftest.py        # Pytest fixtures & synthetic PDF generator
¦   ¦   +-- test_auth.py       # Authentication unit & API tests
¦   ¦   +-- test_authorization.py # Authorization, ownership & IDOR tests
¦   ¦   +-- test_chunker.py    # Document chunker unit tests
¦   ¦   +-- test_config.py     # Configuration tests
¦   ¦   +-- test_documents.py  # Document ingestion & storage tests
¦   ¦   +-- test_embeddings.py # Embedding provider & caching tests
¦   ¦   +-- test_errors.py     # Error handling tests
¦   ¦   +-- test_factory.py    # App factory tests
¦   ¦   +-- test_health.py     # Health smoke test
¦   ¦   +-- test_pgvector_integration.py # Live Neon PostgreSQL + pgvector tests
¦   ¦   +-- test_processing.py # Document processing & OCR tests
¦   ¦   +-- test_processing_security.py # Processing IDOR & security tests
¦   ¦   +-- test_retrieval.py  # Indexing & retrieval service tests
¦   ¦   +-- test_retrieval_security.py # Retrieval IDOR & cross-tenant tests
¦   ¦   +-- test_security_regressions.py # Ingestion security regression tests
¦   +-- pyproject.toml         # Ruff, Mypy, and Pytest configuration
¦   +-- requirements.txt       # Pinned Python dependencies
+-- frontend/
¦   +-- src/
¦   ¦   +-- components/
¦   ¦   ¦   +-- Auth/          # LoginForm & RegisterForm
¦   ¦   ¦   +-- Documents/     # DocumentUpload, DocumentList, RetrievalSearch, DocumentsManager
¦   ¦   ¦   +-- ErrorBoundary/ # Resilient React ErrorBoundary
¦   ¦   ¦   +-- Shell/         # Accessible Header, Footer, MainLayout
¦   ¦   +-- context/           # AuthContext & useAuth hook
¦   ¦   +-- types/             # TypeScript definitions (auth, documents, retrieval)
¦   ¦   +-- App.tsx            # Main application shell
¦   ¦   +-- App.test.tsx       # Shell tests
¦   ¦   +-- config.ts          # Safe frontend configuration
¦   ¦   +-- setupTests.ts      # Test setup & matchers
¦   ¦   +-- main.tsx           # React entry point
¦   ¦   +-- App.css
¦   ¦   +-- index.css
¦   +-- eslint.config.js       # ESLint configuration
¦   +-- index.html
¦   +-- package.json           # Pinned npm dependencies & scripts
¦   +-- tsconfig.json          # TypeScript compiler configuration
¦   +-- vite.config.ts         # Vite bundler & Vitest test runner
+-- docs/
¦   +-- decisions/             # Architecture Decision Records (ADRs 0001-0004)
¦   +-- progress-tracker.md    # Master Progress Tracker
+-- scripts/
¦   +-- check.sh               # Unix full-suite quality & security runner
¦   +-- check.ps1              # Windows full-suite quality & security runner
+-- .env.example               # Safe environment configuration template
+-- .gitignore                 # Exclusion rules
+-- README.md                  # Project overview & documentation
```

---

## Getting Started

### Prerequisites

- **Python**: >= 3.11 (tested on 3.12 / 3.13)
- **Node.js**: >= 20.x
- **npm**: >= 10.x

---

### Quick Start (Full Quality & Security Verification)

Run the unified project quality suite:

- **Linux / macOS**:
  ```bash
  bash scripts/check.sh
  ```

- **Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/check.ps1
  ```

---

### Backend Setup

1. Navigate to `backend/` and set up virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run security and unit tests:
   ```bash
   pytest
   ```

3. Run linting and type checking:
   ```bash
   ruff check .
   ruff format --check .
   mypy app
   ```

4. Start backend server:
   ```bash
   python -m flask --app "app:create_app()" run --port 5000
   ```

---

### Frontend Setup

1. Navigate to `frontend/` and install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run tests:
   ```bash
   npm run test
   ```

3. Run code quality checks:
   ```bash
   npm run lint
   npm run format:check
   npm run typecheck
   ```

4. Start frontend server:
   ```bash
   npm run dev
   ```

---

## Continuous Integration (CI)

GitHub Actions workflow (`.github/workflows/ci.yml`) executes on every commit and PR:
- **Backend**: Python 3.12, dependency installation, `ruff check`, `ruff format --check`, `mypy app`, and complete `pytest` security suite.
- **Frontend**: Node 20, `npm ci`, `prettier --check`, `eslint`, `tsc --noEmit`, `vitest run`, and `vite build`.

---

## Architectural Constraints

- **Single Reasoning Gateway**: In later phases, `reasoning/` will be the ONLY application module directly invoking generative LLM APIs.
- **Evidence-Grounded**: All document analyses require verifiable citations and traceability.
- **Tenant Isolation**: All resource operations are authenticated and strictly scoped to the authenticated user ID.
