# ADR-0002: Secure Document Ingestion, Storage Abstraction, and Lifecycle Architecture

## Status
Accepted

## Context
ClarityKit requires a secure, isolated, and deterministic document ingestion pipeline to accept and manage user-submitted legal documents (specifically PDF files initially) before downstream intelligence pipelines (OCR, chunking, embeddings, and reasoning) are applied in later phases.

## Decision

### 1. Document Resource Model & Ownership
- **Entity**: `Document` representing uploaded document metadata (`document_id`, `user_id`, `filename`, `content_type`, `file_size_bytes`, `storage_key`, `content_hash`, `status`, `created_at`, `updated_at`, `error_message`).
- **Ownership**: The server is the sole authority for ownership. `user_id` is always set from `g.current_user.user_id`. Client-provided owner parameters in bodies or URLs are strictly ignored.

### 2. File Validation & Security Boundary
- **Supported Formats**: Strictly `.pdf` (with MIME `application/pdf` and magic bytes `%PDF-`).
- **Signature / Magic Byte Check**: Server inspects the binary header (`%PDF-` / `\x25\x50\x44\x46\x2D`) to block executable or arbitrary file uploads masquerading with a `.pdf` extension.
- **Size Limits**: Enforced server-side via `MAX_UPLOAD_SIZE_BYTES` (default 20MB, configurable via environment). Oversized and zero-byte files are rejected immediately before storage.
- **Filename Sanitization**: Original filenames are sanitized to prevent directory traversal (`../`, `..\`, absolute paths, null bytes, control characters, Windows device names). Sanitized original filenames are stored purely as display metadata; internal storage paths never use user-controlled filenames.

### 3. Storage Abstraction & Tenant Isolation
- **Interface**: `StorageService` interface abstracting storage operations (`save`, `get`, `delete`, `exists`, `generate_storage_key`).
- **Key Generation**: Storage keys are generated server-side using UUIDs namespaced by user: `users/{user_id}/documents/{document_id}.pdf`.
- **Local Adapter**: `LocalStorageService` enforces strict path containment inside the configured `STORAGE_ROOT` directory. Any attempt to traverse outside `STORAGE_ROOT` raises `StorageSecurityError`.
- **Portability**: The abstraction enables seamless transition to cloud object storage (AWS S3, Google Cloud Storage, Azure Blob Storage) in future phases without altering business logic.

### 4. Document Lifecycle & State Model
- **States**:
  - `QUEUED`: File has been safely validated and stored in storage; metadata record created; ready for Phase 4 processing.
  - `PROCESSING`: Downstream processing / text extraction in progress (Phase 4+).
  - `READY`: Processing complete and intelligence layers available (Phase 4+).
  - `FAILED`: Ingestion or processing encountered an unrecoverable failure.
  - `DELETED`: Document has been removed from storage and metadata updated/purged.
- *Note for Phase 3*: Initial successful ingestion places documents into the `QUEUED` state (representing safe receipt awaiting processing).

### 5. Atomic Ingestion & Cleanup
- If storage write fails, metadata record creation is aborted.
- If metadata record persistence fails, any stored file artifact is automatically unlinked/deleted to prevent orphaned sensitive files.

### 6. Strict IDOR Protection
- `GET /api/documents` lists only documents belonging to the authenticated user (server-side scoped query).
- `GET /api/documents/<document_id>` and `DELETE /api/documents/<document_id>` enforce `@require_ownership`. Accessing a nonexistent document or a document owned by another user returns `HTTP 404 Not Found` (never 403) to prevent existence enumeration.

## Consequences
- **Positive**: Complete user data isolation, airtight protection against path traversal and MIME spoofing, clear separation of storage and persistence layers, resilient error cleanup.
- **Neutral**: Filesystem storage root requires write permissions in local development environments.
