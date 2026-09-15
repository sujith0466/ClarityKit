# ADR-0003: Document Processing, Page-Aware Text Extraction, and OCR Fallback Architecture

## Status
Accepted

## Context
In Phase 3, ClarityKit established secure document ingestion and namespaced storage. In Phase 4, uploaded PDF documents must be processed into normalized, page-aware text representations. Downstream phases (chunking, embeddings, evidence grounding, citation tracing) require that every unit of text is unambiguously mapped to its original source page and extraction methodology.

The goal is strictly document text extraction and content foundation—not legal intelligence or LLM interpretation.

## Decision

### 1. Page-Aware Document Representation
- **Structure**: Extracted content is stored as individual DocumentPage records associated with a document_id.
- **Traceability Core**: Every page record contains page_number (1-indexed), 	ext (normalized), extraction_method (
ative | ocr), char_count, word_count, is_empty, ocr_required, processing_duration_ms, and timestamps.
- **Source Integrity**: The original PDF stored in Phase 3 remains the immutable source of truth. Extracted text is an indexing and evidence derivation layer, never a destructive replacement.

### 2. Dual-Engine Extraction Strategy (Native First, OCR Fallback)
- **Native Extraction as Primary**: Digital PDFs contain searchable text streams with accurate glyph encoding and reading order. Native extraction is computationally lightweight and deterministic.
- **OCR Fallback**: Scanned documents or image-only pages contain little to no native text. When a page has fewer than the configurable character threshold (e.g. < 30 characters) or is flagged as an image/scan, the system triggers OCR fallback for that specific page.
- **Hybrid Page-Level Granularity**: In mixed documents (e.g., contract body with scanned signature pages), native pages use extraction_method= native, while scanned pages use extraction_method=ocr. Documents are never blindly converted to OCR in full unless every page requires it.

### 3. OCR Provider Abstraction
- **Protocol**: OCRProvider abstract protocol declaring extract_text(image_bytes: bytes) -> str and is_available() -> bool.
- **Implementations**:
  - TesseractOCRProvider: Integrates with local Tesseract / pytesseract binary when present.
  - MockOCRProvider / FallbackOCRProvider: Deterministic fallback for test environments and headless deployments without external Tesseract dependencies.
- **Extensibility**: Cloud vision adapters (AWS Textract, Google Cloud Vision) can be added as drop-in implementations without modifying business logic.

### 4. Conservative Text Normalization
- Normalization preserves legal integrity:
  - Standardizes newline sequences (\r\n -> \n).
  - Strips non-printable control characters and null bytes (\x00).
  - Trims excessive trailing whitespace while preserving legal structure, paragraph breaks, indentation, and list numbering.
  - Strictly **FORBIDS** paraphrasing, summarization, spelling/grammar alterations, number transformations, or LLM interpretation.

### 5. Processing State Machine & Lifecycle
- **Transitions**:
  - QUEUED -> PROCESSING -> READY (on successful page extraction and persistence).
  - QUEUED -> PROCESSING -> FAILED (on corrupted PDF, unreadable stream, or unrecoverable processing error).
- **Invalid Transitions**: Prohibited (e.g., cannot transition from DELETED or UPLOADING to PROCESSING).

### 6. Idempotency & Safe Reprocessing
- Unique composite boundary on (document_id, page_number).
- Reprocessing a document replaces previous page extractions atomically in the repository, preventing duplicate page accumulation on retries.

### 7. Security, Resource Containment & Temporary File Handling
- **Containment**: Reads PDF bytes strictly from the StorageService using the document''s server-assigned storage key. No arbitrary paths or client file references are permitted.
- **Resource Limits**: Configurable maximum page limit (e.g. 500 pages per document) to protect against memory exhaustion and decompression attacks.
- **Temporary File Hygiene**: Any temporary images or page dumps generated during OCR are created in isolated temporary directories and deleted in 	ry...finally blocks.

## Consequences
- **Positive**: Complete page-level evidence traceability for Phase 5+, robust handling of both native and scanned legal documents, zero speculative infrastructure (no Redis/Celery required for synchronous pipeline).
- **Neutral**: OCR on large multi-page scans requires CPU processing time; page limits guard system throughput.
