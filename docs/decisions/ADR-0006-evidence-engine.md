# ADR-0006: Evidence Engine & Citation Verification Substrate

## Status
Accepted / Phase 7 Implementation

## Context
Following Phase 6 (Structured Extraction), ClarityKit extracts structured legal facts (Parties, Clauses, Obligations, Dates, Review Flags) linked to document page numbers and source spans.

ClarityKit's foundational product principle is:
> **NO EVIDENCE, NO DOCUMENT-SPECIFIC CLAIM.**

To uphold this principle without fabricating citations or hallucinating claims, ClarityKit requires a dedicated **Evidence Engine** to perform mechanical verification of all document-specific citations.

## Decision

### 1. Separation of Citation Validity vs. Grounding Correctness
- **Citation Validity**: A mechanically testable property answering: *"Does this referenced text span exist at the claimed document page location?"* (Target: 100% of rendered document-specific claims must have structurally valid citations).
- **Grounding Correctness**: A semantic truth property answering: *"Does the cited evidence actually support the meaning of the claim?"* This cannot be proven merely by substring matching and is evaluated via human-reviewed golden evaluation sets.
- The UI, API, and documentation must NEVER present mechanical validity as proof of legal correctness or enforceability.

### 2. DocumentPage Text as the Sole Source of Truth
- `DocumentPage.text` is the authoritative source for all evidence resolution.
- Stored `source_text` in database records is strictly a display snapshot; resolution always evaluates against authoritative `DocumentPage` entities.

### 3. Mechanical Resolution & Strict Rejection
- `SourceSpanResolver` executes:
  1. Exact substring matching on authoritative page text.
  2. Safe normalized-whitespace matching (handling Unicode spaces, line breaks, multi-spaces without modifying words, casing, or punctuation).
  3. Contiguous cross-page matching with boundary validation.
- **Strict Prohibition**: The resolver NEVER invents citations, NEVER selects "nearest" text, and NEVER moves citations across mismatched pages. Unmatched spans are marked `INVALID`.

### 4. Deterministic Evidence Coverage
- Evidence coverage is calculated deterministically:
  $$\\text{coverage} = \\frac{\\text{valid\\_claims}}{\\text{total\\_claims}}$$
- Coverage is never rounded upward to 100% if any unevidenced or invalid claim exists.

### 5. Multi-Tenant Persistence & Delete Cascade
- Migration `0004_evidence_engine.sql` establishes `document_evidence_records` with `ON DELETE CASCADE` referencing `documents(id)`.
- SQL-level tenant isolation (`JOIN documents d ON d.id = target.document_id WHERE d.user_id = %s`) prevents IDOR and cross-tenant leakage.

## Consequences
- 100% mechanical traceability for all document-specific legal claims.
- Immediate rejection of fabricated or tampered source spans.
- Solid substrate for Phase 8 (Trust & Safety) and Phase 9 (Grounded Q&A).
