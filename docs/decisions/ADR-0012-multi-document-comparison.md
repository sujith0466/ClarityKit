# ADR-0012: Multi-Document Comparison & Consistency Analysis

## Status
Accepted

## Context
ClarityKit provides evidence-grounded document understanding, extraction, trust & safety classification, Q&A, and lawyer-preparation briefs for individual legal documents. Users frequently deal with sets of related legal documents (e.g., employment offer letters and employment contracts, commercial leases and lease addenda, NDAs and amendments, service agreements and statements of work).

Users need the ability to compare multiple related documents to identify:
1. Explicit factual differences (e.g., compensation numbers, differing dates, differing party roles, conflicting notice periods).
2. Provisions present in one document but not identified in extracted content of another.
3. Potential inconsistencies across documents.
4. Grounded evidence citations for every document-specific finding.
5. Neutral, objective questions to bring to a qualified legal professional.

At the same time, ClarityKit must strictly preserve its core product positioning:
> **NO EVIDENCE → NO DOCUMENT-SPECIFIC CLAIM.**  
> ClarityKit is an evidence-grounded legal document understanding platform that transforms complex legal documents into understandable, traceable, and actionable information **without pretending to be a lawyer**.

Multi-document comparison must never become an ungrounded legal judgment engine. It answers *"What differs between these documents?"* and *"Where do these documents appear inconsistent?"*—it **never** answers *"Which document legally wins?"*, *"Which clause is legally valid?"*, or *"Was the contract breached?"*.

## Decision

### 1. Bounded Document Set & Tenant Isolation
- Comparisons are strictly bounded to **2 to 5 documents** per comparison set ($2 \le N \le 5$). Unbounded comparison sets are rejected at the API boundary.
- All documents in a comparison must belong to the authenticated user/tenant. Any request referencing non-owned or non-existent documents returns HTTP 404 (preventing cross-tenant IDOR and document existence leakage).

### 2. Multi-Document Domain Models & Categories
- **Comparison Categories**:
  - `PARTIES`: Differences in entity names, signatory identities, and designated roles.
  - `DATES`: Differences in effective dates, expiration dates, execution dates, and milestone deadlines.
  - `OBLIGATIONS`: Differences in duties, notice requirements, deliverables, and performance covenants.
  - `TERMINATION`: Differences in termination triggers, cure periods, and notice periods.
  - `PAYMENT`: Differences in compensation, rent amounts, fees, and payment schedules.
  - `DURATION`: Differences in term length, renewal mechanisms, and survival clauses.
  - `CLAUSE`: General clause variations (governing law, dispute resolution, confidentiality).
  - `DEFINITIONS`: Differing defined terms.
  - `NOTICE`: Differing notice addresses, transmission methods, or timeframes.
  - `OTHER`: Uncategorized factual differences.
- **Difference Classifications** (Domain states, strictly separated from Phase 8 Safety Statuses):
  - `MATCH`: Both/all documents explicitly state congruent terms/facts.
  - `DIFFERENT`: Documents state different explicit terms/values on the same subject.
  - `PRESENT_IN_ONE_ONLY`: Provision identified in one document but not identified in the extracted content of the other(s).
  - `POTENTIAL_INCONSISTENCY`: Provisions directly contradict or appear conflicting (e.g. conflicting start dates, conflicting notice days).
  - `UNRESOLVED`: Candidate difference could not be mechanically verified or lacks conclusive extraction.

### 3. Evidence Engine & Grounding Invariant
- `DocumentEvidenceRef` is strictly a projection structure.
- All citations and source spans are mechanically validated exclusively via Phase 7 `EvidenceValidator` against authoritative `DocumentPage.text`.
- **No duplicate evidence resolver or citation parser is created.**
- Every document-specific finding must contain validated source evidence from all referenced documents. Findings with invalid or missing evidence are dropped or marked `UNSUPPORTED`/`UNRESOLVED`.

### 4. Candidate Matching $\neq$ Confirmed Equivalence
- Semantic clause embeddings and heading similarity serve strictly as **candidate generation mechanisms**.
- Semantic similarity is never treated as proof of legal or substantive equivalence.
- All findings are validated against actual extracted text and source spans.

### 5. Safe Phrasing Invariants
- For `PRESENT_IN_ONE_ONLY` findings, mandatory phrasing is enforced:
  > *"A corresponding provision was identified in Document A but was not identified in the extracted content of Document B."*
- The system must never claim that a provision *"does not exist in the document"* merely because it was not identified in extracted content.
- The system must never state which document *"controls"*, *"overrides"*, or *"is legally valid"*.

### 6. Neutral Legal Professional Preparation Questions
- Detected differences and potential inconsistencies generate neutral questions to ask a lawyer (reusing Phase 11 question structures and deterministic templates).
- Questions are strictly objective (e.g., *"Which agreement governs the notice period, and what factors determine that?"* rather than biased or conclusory statements).

### 7. Frozen Trust & Safety Taxonomy
- Phase 8 Trust Tiers remain strictly: `DOCUMENT_FACT`, `GENERAL_INFORMATION`, `INTERPRETATION`, `PROFESSIONAL_REVIEW_NEEDED`.
- Phase 8 Safety Statuses remain strictly: `SAFE`, `LIMITED`, `REVIEW_REQUIRED`, `UNSUPPORTED`.
- Comparison classifications are domain states and are not added to or conflated with Phase 8 safety statuses.

### 8. Database Persistence & Document Deletion Lifecycle
- Migration `0008_document_comparisons.sql` creates `document_comparisons` table referencing `users(id)` with cascade deletion.
- Comparison records reference document IDs; when a source document is deleted, the comparison is cleaned up or marked unavailable, preserving tenant isolation without orphaned records.
- Sensitive derived legal text is never written to general application logs.

### 9. Performance & Scope Boundaries
- Deterministic comparison runs first on structured extractions (parties, dates, obligations, durations).
- Candidate narrowing ensures $O(N)$ and bounded operations without $N^2$ generative LLM calls.
- Comparison-aware Q&A is excluded from Phase 13 required scope.

## Consequences
- Clean composition over existing Phase 5 retrieval, Phase 6 extraction, Phase 7 evidence, Phase 8 trust/safety, and Phase 9 source inspector.
- Zero architectural regressions or duplicate engines.
- Comprehensive accessibility and security adherence matching Phases 0–12.
