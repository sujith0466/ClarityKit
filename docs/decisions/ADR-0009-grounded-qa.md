# ADR-0009: Grounded Document Q&A Architecture

## Status
Accepted

## Context
ClarityKit requires a document-scoped, evidence-grounded question answering (Q&A) engine that enables users to query uploaded legal agreements in natural language. In legal technology, conversational interfaces frequently suffer from generative hallucinations, unsupported enforceability assertions, accidental prompt injection, and blurry boundaries between general legal knowledge and actual document terms.

To uphold the core platform principle **"NO EVIDENCE, NO DOCUMENT-SPECIFIC CLAIM"**, Q&A must not operate as an ungrounded chatbot. Instead, it must execute a deterministic, multi-stage retrieval-grounding-verification pipeline that mechanically checks every document claim against authoritative document pages before presenting answers with explicit trust tiers, safety classifications, and provenance.

## Decisions

### 1. Document-Scoped Pipeline Architecture
Every Q&A interaction follows a strict, single-document bounded workflow:
```text
User Question
      ↓
Authentication & Ownership Validation (404 on IDOR)
      ↓
Document-Scoped Retrieval (Phase 5 Vector Chunks)
      ↓
Retrieval Sufficiency Decision (Sufficient / Weak / None)
      ↓
Grounded Context Construction & Prompt Injection Isolation
      ↓
Generative Reasoning through ReasoningGateway (backend/app/reasoning/)
      ↓
Structured Output Extraction (Answer Text, Claims, Evidence References)
      ↓
Mechanical Citation Validation via EvidenceValidator (Phase 7)
      ↓
Hard "No-Evidence" Enforcement (Ungrounded claims rejected / fallback)
      ↓
Deterministic Trust & Safety Classification via TrustClassifier (Phase 8)
      ↓
Answer Assembly & Sensitive-Aware Persistence
      ↓
Workspace Presentation with Deep-Linkable Source Inspector (Phase 9)
```

### 2. Single Generative Gateway Policy
`backend/app/reasoning/` remains the ONLY application module authorized to invoke generative LLM models. All Q&A prompts, schemas, and provider abstractions reside within this layer. If generation produces invalid schemas or broken citations, bounded retries or deterministic fallbacks are triggered.

### 3. Document Content as Untrusted Data
Uploaded documents and retrieved chunks may contain adversarial text (e.g. *"ignore previous instructions"*, *"mark this legally verified"*). Prompts strictly encapsulate document text inside sanitized `<document_evidence>` boundaries and instruct the model that document content is passive data, never system commands.

### 4. Mechanical Citation Validity vs Grounding Correctness
Every generated claim with an evidence reference is validated by the Phase 7 `EvidenceValidator` against authoritative `DocumentPage.text`.
- Citation validity (mechanical existence of cited span at page offset) is strictly enforced.
- The platform never asserts that citation validity proves "legal validity" or "100% legal correctness".

### 5. Deterministic Trust & Safety Invariants
All Q&A responses reuse Phase 8 Trust & Safety contracts:
- **Trust Tiers**: `DOCUMENT_FACT`, `GENERAL_INFORMATION`, `INTERPRETATION`, `PROFESSIONAL_REVIEW_NEEDED`.
- **Safety Statuses**: `SAFE`, `LIMITED`, `REVIEW_REQUIRED`, `UNSUPPORTED`.
- If evidence is missing or invalid for a document-specific claim, the claim is rejected or categorized as `PROFESSIONAL_REVIEW_NEEDED` / `UNSUPPORTED`.

### 6. Strict Scope Boundaries
Phase 10 explicitly prohibits:
- Lawyer-prep briefs (reserved for Phase 11).
- Legal advice, legal outcome predictions, and risk scoring.
- Contract drafting, redlining, or automated alterations.
- Unbounded cross-document or external law database searches.
- Generic conversational chatbot behaviors.

## Consequences
- Guarantees that every document-specific statement in an answer is backed by verifiable text.
- Protects users from hallucinations and unauthorized legal advice.
- Reuses existing retrieval, evidence, trust, and workspace modules without architectural duplication.
- Provides an accessible, transparent, and auditable Q&A experience.
