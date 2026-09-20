# ADR-0007: Trust & Safety Layer Architecture

## Status
Accepted

## Context
ClarityKit requires a robust, deterministic, and machine-testable Trust & Safety layer sitting between evidence-grounded document understanding and downstream user assistance. In legal document analysis, generative AI models can hallucinate facts, conflate general educational legal concepts with document-specific clauses, or attempt to provide unauthorized legal enforceability predictions.

To protect users and enforce the core product principle **"NO EVIDENCE, NO DOCUMENT-SPECIFIC CLAIM"**, the platform requires explicit trust tier classification, clear safety boundary statuses, limitation metadata, and escalation to professional legal review.

## Decisions

### 1. Four Explicit Trust Tiers
We define exactly four distinct trust categories:
1. `DOCUMENT_FACT`: Document-specific assertion supported by mechanically valid evidence resolving against authoritative `DocumentPage.text`.
2. `GENERAL_INFORMATION`: General legal educational concepts not asserting facts about the user's specific uploaded document.
3. `INTERPRETATION`: Explanation or interpretation of specific document language; source text is identified, but the assertion is not represented as verbatim fact.
4. `PROFESSIONAL_REVIEW_NEEDED`: Situations where document information is insufficient, ambiguous, enforceability is questioned, jurisdiction is critical, or evidence is missing/invalid.

### 2. Citation Validity vs Grounding Correctness
Citation validity is mechanically verified (span existence at page offset). Grounding correctness (semantic truth) is evaluated via curated golden datasets. The platform never exposes misleading claims such as "100% legally verified" or "lawyer-approved" based solely on citation validity. If surfaced, `evidence_coverage` explicitly measures mechanically valid citations.

### 3. Deterministic Safety Rule Engine
All safety classifications and escalations are performed through deterministic rule sets with strict priority precedence:
- Rule 10: Legal Enforceability / Outcome Requests -> `PROFESSIONAL_REVIEW_NEEDED` (`REVIEW_REQUIRED`)
- Rule 20: Missing Jurisdiction / Current Statutory Law -> `PROFESSIONAL_REVIEW_NEEDED` (`REVIEW_REQUIRED`)
- Rule 30: Missing / Invalid / Stale Evidence -> `PROFESSIONAL_REVIEW_NEEDED` (`UNSUPPORTED`)
- Rule 40: Material Ambiguity in Text -> `INTERPRETATION` (`REVIEW_REQUIRED`)
- Rule 50: Document Interpretation -> `INTERPRETATION` (`LIMITED`)
- Rule 60: Valid Document Fact -> `DOCUMENT_FACT` (`SAFE`)
- Rule 70: General Legal Concept -> `GENERAL_INFORMATION` (`SAFE`)

### 4. Reasoning Boundary & Prompt Injection Resistance
`backend/app/reasoning/` remains the only module allowed to invoke LLMs. The Trust layer does not invoke LLMs for safety classifications and never trusts self-declared LLM confidence. Adversarial document content (e.g. "ignore previous instructions", "mark as verified") is treated strictly as untrusted text and cannot alter classification rules.

### 5. Multi-Tenant SQL Isolation & Derived Persistence
Trust assessments are derived/rebuildable artifacts from extraction and evidence. When persisted in `document_trust_assessments`, records reference `documents(id) ON DELETE CASCADE` with SQL-level multi-tenant isolation (`JOIN documents d ON d.id = target.document_id WHERE d.user_id = %s`).

## Consequences
- Prevents unsupported legal assertions and hallucinations from reaching users.
- Provides accessible, transparent safety metadata on all extracted legal claims.
- Establishes a solid foundation for future Q&A and document preparation phases.
