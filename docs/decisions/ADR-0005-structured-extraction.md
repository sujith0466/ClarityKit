# ADR-0005: Structured Document Extraction & Reasoning Boundary

## Status
Accepted / Phase 6 Implementation

## Context
Following Phase 4 (Document Processing & OCR) and Phase 5 (Chunking, Indexing & Retrieval), documents are stored, extracted into ordered `DocumentPage` entities, and chunked with provenance.

ClarityKit requires a structured extraction layer to extract traceable legal facts from documents:
1. **Parties**: Identifiable entities and their roles (e.g., Employer, Employee, Landlord, Tenant).
2. **Clauses**: Sections and provisions classified into standard categories (e.g., Confidentiality, Termination, Liability).
3. **Obligations**: Specific duties and requirements expressing legal duty (obligor, duty, trigger, deadline).
4. **Important Dates**: Explicit dates, renewal terms, notice windows, and payment schedules.
5. **Review Flags**: Neutral advisory flags highlighting ambiguous terms, broad covenants, or potential missing terms for user attention.

## Decision

### 1. Dedicated Extraction Module & LLM Reasoning Boundary
- Structured extraction logic resides exclusively in `backend/app/extraction/`.
- The module `backend/app/reasoning/` is established as the **SINGLE GATEWAY** for generative reasoning. `app.extraction` consumes the reasoning abstraction (`ReasoningGateway`) and does NOT directly import or call external LLM SDKs.
- `DeterministicStructuredExtractionProvider` is implemented in `reasoning/` as a **TEST/DEVELOPMENT PROVIDER** using pattern recognition, regex heuristics, and modal verb parsing. It provides deterministic, zero-dependency offline extraction without pretending to be a trained neural model.

### 2. Strict Schema Validation & Defense Against Untrusted Input
- All extraction outputs are strictly validated against Pydantic / dataclass domain schemas before persistence.
- Document text is treated as **UNTRUSTED DATA**:
  - Directives such as "ignore previous instructions" or fake system messages embedded in legal text are parsed strictly as document data and cannot alter extraction logic or application instructions.
  - Missing or malformed extraction records fail safely without fabricating placeholder data.

### 3. Source Provenance Preservation
- Every extracted item carries explicit provenance: `document_id`, `page_start`/`page_end`, and `source_span`.
- Provenance spans are structurally validated against corresponding `DocumentPage` text.
- Note: Structural span validation confirms source linkage; full semantic evidence verification is deferred to Phase 7 (Evidence Engine).

### 4. Neutral Review Flags (No Legal Advice)
- Review flags provide neutral informational summaries (e.g., "The notice period of 90 days appears longer than standard commercial terms and may warrant closer review").
- Absolute prohibition against legal conclusions, validity claims, or advice on whether to sign.

### 5. Multi-Tenant Database Persistence & Idempotency
- Migration `0003_structured_extraction.sql` defines:
  - `extracted_parties`
  - `extracted_clauses`
  - `extracted_obligations`
  - `extracted_dates`
  - `extracted_review_flags`
- All tables reference `documents(id) ON DELETE CASCADE`.
- Tenant isolation is enforced in SQL queries (`JOIN documents d ON d.id = target.document_id WHERE d.user_id = :user_id`).
- Re-extraction is idempotent: existing extraction records for a document are atomically replaced.
- Fallback `InMemoryExtractionRepository` is provided for offline testing when `DATABASE_URL` is omitted.

## Consequences
- Clean, decoupled extraction substrate ready for Phase 7 Evidence Grounding.
- 100% provenance tracking for all extracted entities.
- Full tenant isolation and IDOR defense at the database query boundary.
- Zero generative LLM calls outside `reasoning/`.