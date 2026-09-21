# ADR-0010: Lawyer-Preparation Brief Architecture & Safety Boundaries

## Status
Accepted

## Context
ClarityKit provides structured legal document understanding (Phase 6), mechanical evidence validation (Phase 7), deterministic trust & safety classification (Phase 8), an interactive document understanding workspace (Phase 9), and grounded document Q&A (Phase 10).

Users consulting a legal professional often face high costs and cognitive overhead due to disorganized documents, unclear timelines, missing contextual facts, and underspecified questions. 

To bridge the gap between user understanding and professional consultation without providing unauthorized legal advice, Phase 11 introduces the **Lawyer-Preparation Brief**.

## Core Product & Evidence Principles
1. **Core Product Principle**: *Prepare the user to ask better questions. Do NOT decide the legal answer for the user.*
2. **Core Evidence Principle**: *NO EVIDENCE → NO DOCUMENT-SPECIFIC CLAIM.*
3. **Non-Legal Advice Guarantee**: The brief is explicitly an evidence-grounded preparation artifact. It does not provide legal advice, legal opinions, outcome predictions, enforceability determinations, or contract redlining.

## Decision Drivers
- **Deterministic Assembly Over Hallucination**: The brief is primarily an evidence-backed synthesis of already-verified Phase 6 extractions, Phase 7 evidence records, Phase 8 trust assessments, and Phase 10 grounded Q&A findings.
- **Strict Provenance**: Every document-derived item in the brief retains its `document_id`, `evidence_id`, page/section references, trust tier, and source type (`EXTRACTION`, `EVIDENCE`, `GROUNDED_QA`, `USER_INPUT`).
- **No Second Engines**: Reuses existing `EvidenceValidator`, authoritative `DocumentPage.text`, and `TrustClassifier`. No duplicate citation validators, parallel trust classifiers, or separate source viewers are created.
- **Safety & Forbidden Conclusions Filter**: Deterministic validation blocks conclusions such as "you should sign", "this is illegal", "you will win", or "the counterparty breached the contract".
- **Prompt Injection Sandboxing**: All document text is treated strictly as untrusted passive data within `<document_evidence>` sandboxes.
- **Safe Export Layer**: In-memory PDF export renders user-visible brief sections, evidence references, and disclaimers without leaking raw prompts, internal reasoning traces, tokens, or system metadata.

## Architectural Design

### 1. Source Hierarchy
The preparation brief is synthesized following a strict priority order:
1. **Phase 6 Structured Extraction**: Parties, primary clauses, rights/obligations, key dates, review flags.
2. **Phase 7 Validated Evidence**: Verifiable character-span linkages and mechanical validity against `DocumentPage.text`.
3. **Phase 8 Trust & Safety**: Deterministic trust tiers (`DOCUMENT_FACT`, `GENERAL_INFORMATION`, `INTERPRETATION`, `PROFESSIONAL_REVIEW_NEEDED`) and safety statuses (`SAFE`, `LIMITED`, `REVIEW_REQUIRED`, `UNSUPPORTED`).
4. **Phase 10 Grounded Q&A**: Persisted, grounded Q&A answers and validated citations.
5. **User-Provided Context**: Clarifications provided by the authenticated user if applicable.

### 2. Brief Structure
The brief is organized into 12 structured, neutral sections:
1. **Preparation Overview**: High-level neutral document description and synthesis metrics.
2. **Document Snapshot**: Essential metadata (title, page count, document type if authoritative).
3. **Key Parties & Entities**: Identified contracting parties, roles, and source locations.
4. **Important Clauses & Obligations**: Core duties, conditions, triggers, and deadlines.
5. **Important Dates & Terms**: Identified calendar milestones, effective dates, and renewal periods.
6. **Review Areas**: Identified non-standard or restrictive terms (e.g. non-compete covenants, unilateral changes) presented as factual observations requiring professional review.
7. **What the Document Does Not Establish (Open Questions)**: Crucial safety section explicitly identifying missing referenced policies, unstated dates, omitted jurisdictions, or unrecorded events.
8. **Questions to Ask a Legal Professional**: Neutral, high-leverage questions organized by topic to guide attorney discussions.
9. **Facts to Confirm**: Non-assertive checklist of external records or historical events the user should consider gathering.
10. **Documents to Bring**: Practical checklist of referenced exhibits, amendments, notices, or email records.
11. **Grounded Q&A Findings**: Highlighted takeaways from prior grounded Q&A messages with valid evidence.
12. **Sources & Verifiable Evidence**: Detailed citations linked to authoritative document page text.

### 3. Tenant Isolation & Database Schema
- Stored in `preparation_briefs` table referencing `documents(id)` with `ON DELETE CASCADE`.
- SQL tenant boundary enforced via `JOIN documents d ON d.id = target.document_id WHERE d.user_id = %s`.
- Non-owned resources return HTTP `404 Not Found`.

### 4. PDF Export
- Deterministic, standards-compliant PDF exporter generates printable/exportable briefs.
- Contains only user-facing content, page references, and disclaimer headers.
- Completely excludes internal system prompts, developer instructions, and API keys.

## Consequences
- **Positive**: Users receive clear, organized, evidence-traceable briefs that maximize the efficiency of consultations with lawyers.
- **Positive**: Strict deterministic validation prevents unauthorized practice of law and hallucinated legal advice.
- **Boundary**: Does not support contract redlining, legal outcome prediction, lawyer marketplace integration, or multi-document comparison.
