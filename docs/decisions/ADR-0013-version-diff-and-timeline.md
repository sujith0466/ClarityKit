# ADR-0013: Document Version Diff and Deadline/Obligation Timeline Architecture

## Status
ACCEPTED (Phase 14)

## Context
ClarityKit requires evidence-grounded advanced capabilities to assist users when reviewing iterative revisions of the same legal document (Version Diff) and navigating time-sensitive contractual milestones (Deadline & Obligation Timeline).

These features must adhere to ClarityKit's core principle:
`NO EVIDENCE, NO DOCUMENT-SPECIFIC CLAIM.`

The system must never provide legal advice, proclaim legal superiority of a revision, declare breach or liability, or invent dates based on unstated jurisdictional conventions.

## Decisions

### 1. Document Version Diff Boundary
- **User-Declared Version Pairing:** Version Diff compares two user-selected documents designated as **Version 1 (Base)** and **Version 2 (Revised)**.
- **Relational Integrity:** Both versions must exist in the user's workspace, have status `READY`, and be distinct documents ($V_1 \ne V_2$).
- **Version Identity & Structural Compatibility Boundary:**
  - *Schema Reality:* In the current schema (Phases 1–14), documents do not possess a persistent `version_family_id` column on the `documents` table.
  - *Boundary Rule:* To avoid fragile filename heuristics while preventing arbitrary, unrelated documents from being silently presented as versions of the same agreement, `VersionDiffValidator` enforces structured entity and category compatibility.
  - *Party Compatibility:* When both documents contain extracted parties ($|P_1| > 0$ and $|P_2| > 0$), at least one shared legal entity must overlap. If party sets are strictly disjoint, the pair is rejected with `InvalidVersionDiffInputError`.
  - *Category Compatibility:* When both documents contain structured clauses ($|C_1| \ge 2$ and $|C_2| \ge 2$), completely disjoint clause categories are rejected with `InvalidVersionDiffInputError`.
  - *Multi-Document Scope:* Users seeking to compare separate, distinct agreements across different parties/domains must use Multi-Document Comparison (Phase 13).
- **Neutral Classifications:** Domain differences are classified as:
  - `ADDED`: Content/clause/obligation identified in Version 2 with no corresponding match in Version 1.
  - `REMOVED`: Content/clause/obligation identified in Version 1 with no corresponding match in Version 2.
  - `MODIFIED`: Corresponding provisions identified in both versions with variations in text, notice periods, dates, or obligors.
  - `UNCHANGED`: Provisions identical in substance across both versions.
  - `POTENTIAL_CHANGE`: Semantic/structural variations requiring user review.
  - `UNRESOLVED`: Candidate change where mechanical evidence could not be verified.
- **Neutral Language Invariant:** The engine describes changes objectively (e.g., *"Version 2 specifies a 60-day notice period, whereas Version 1 specified a 30-day notice period"*). It strictly prohibits value judgments (*"The employer weakened your rights"*, *"Version 2 is legally worse"*).

### 2. Phase 7 Evidence Validation Reuse
- Phase 14 routes all citation validation through the authoritative Phase 7 [`EvidenceValidator`](file:///d:/ClarityKit/backend/app/evidence/validators.py).
- Candidate findings construct Phase 7 [`Claim`](file:///d:/ClarityKit/backend/app/evidence/models.py) objects backed by [`EvidenceReference`](file:///d:/ClarityKit/backend/app/evidence/models.py) and execute `EvidenceValidator.validate_claim(claim, page_texts)`.
- Internal span resolution uses Phase 7 mechanical resolution. If any citation fails mechanical verification, the finding is marked `UNRESOLVED` and flagged with `SafetyStatus.REVIEW_REQUIRED`.

### 3. Deadline & Obligation Timeline Architecture
- **Chronological Synthesis:** Combines Phase 6 extracted dates, obligations, and clauses for an individual document into a unified chronological stream.
- **Date Categories:**
  - `FIXED_DATE`: Explicit calendar date directly stated in the document (e.g. *"January 15, 2026"*).
  - `RELATIVE_DEADLINE`: Deadline expressed relative to an event or trigger (e.g. *"30 days after invoice"*).
  - `DURATION`: Time span or period (e.g. *"Term of 2 years"*).
  - `RECURRING`: Recurring event (e.g. *"Monthly on the 1st"*).
  - `UNSPECIFIED`: Obligation without a fixed or relative date anchor.
- **Explicit vs. Derived Distinction:**
  - `EXPLICIT_FACT`: Date directly stated in the source text (`TrustTier.DOCUMENT_FACT`, `SafetyStatus.SAFE`).
  - `DERIVED`: Mathematically calculated date from a confirmed explicit trigger date and duration. Must explicitly display `inputs_used` and not masquerade as an explicit document fact.
  - `UNRESOLVED_TRIGGER`: Relative deadline where the triggering date is absent or unspecified (`TrustTier.PROFESSIONAL_REVIEW_NEEDED`, `SafetyStatus.REVIEW_REQUIRED`). The system never assumes unstated jurisdictional business-day or holiday rules.

### 4. Database & Relational Schema
- Migration `0009_version_diff_and_timeline.sql`:
  - `document_version_diffs` table with foreign keys `v1_document_id REFERENCES documents(id) ON DELETE CASCADE`, `v2_document_id REFERENCES documents(id) ON DELETE CASCADE`, and `user_id REFERENCES users(id) ON DELETE CASCADE`.
  - `document_timelines` table with foreign key `document_id REFERENCES documents(id) ON DELETE CASCADE` and `user_id REFERENCES users(id) ON DELETE CASCADE`.
- Repositories implement dynamic ownership and document status verification on all read operations as a secondary defense layer.

### 5. API Endpoint Semantics
- `POST /api/version-diffs`: Generate and persist a version diff between two documents.
- `GET /api/version-diffs`: List persisted version diffs.
- `GET /api/version-diffs/<id>`: Retrieve specific version diff.
- `DELETE /api/version-diffs/<id>`: Delete version diff.
- `POST /api/documents/<document_id>/timeline`: Generate and persist document timeline.
- `GET /api/documents/<document_id>/timeline`: Retrieve existing persisted timeline (returns 404 if not yet generated; side-effect free).
- `GET /api/timelines`: List user timelines.
- `DELETE /api/timelines/<id>`: Delete timeline.

## Consequences
- Preserves all Phase 0–13 frozen baselines.
- Provides predictable, evidence-backed version diffing and timeline tracking.
- Eliminates risk of silent hallucination or speculative legal advice.
