# ADR-0008: Document Understanding Workspace Architecture

## Status
Accepted

## Context
ClarityKit requires a cohesive, accessible, interactive Document Understanding Workspace that synthesizes structured legal extraction (Phase 6), mechanical evidence records (Phase 7), and deterministic trust & safety assessments (Phase 8) into a unified visual interface.

Prior to Phase 9, extraction, evidence, and trust reports could be viewed through isolated panels. Users need an integrated cockpit to explore contracting parties, categorized clauses, affirmative/negative obligations, important dates, flagged review areas, mechanical citations, and trust classifications with deep-linkable source inspection.

To uphold the core product principle **"NO EVIDENCE, NO DOCUMENT-SPECIFIC CLAIM"**, the workspace must present all findings with full provenance back to the authoritative `DocumentPage.text`, provide explicit neutral trust labeling, and remain strictly bounded without speculative chat, open-ended generative summarization, or unauthorized legal conclusions.

## Decisions

### 1. Unified Tabbed Workspace Container
We implement `DocumentWorkspace.tsx` as the single container coordinating the document analysis experience across 7 specialized tabs:
1. `Overview`: High-level structured summaries (parties, clauses, obligations, dates, review areas), `evidence_coverage` metric, and explicit non-legal-advice disclaimers.
2. `Parties`: Contracting entities, entity types, roles, and source citations.
3. `Clauses`: Categorized contract clauses with category filter chips, trust tier badges, and source inspection.
4. `Obligations`: Affirmative and negative duties grouped by responsible party with conditions, triggers, and timing.
5. `Important Dates`: Extracted dates, ISO normalized representations, date categories, and source context (strictly without deadline scheduling or reminder engines).
6. `Review Areas`: Flagged items requiring user attention with severity ratings and neutral professional review advisories.
7. `Evidence` & `Trust & Safety`: Integrated sub-views hosting Phase 7 `EvidenceViewer` and Phase 8 `TrustSafetyViewer`.

### 2. Deep-Linkable Source Inspector Modal
Every extracted claim and structured record provides an "Inspect Source" action that opens `SourceInspectorModal.tsx`.
- The modal fetches the authoritative `DocumentPage.text` directly from the server.
- The exact character span (`[start_offset, end_offset]`) is highlighted with semantic `<mark>` elements inside the complete surrounding page context.
- Fallback rendering gracefully handles multi-span matches and missing offsets without application crashes.

### 3. Neutral Terminology & Professional Review Framing
In accordance with ethical legal tech design:
- Trust tiers are rendered using standard neutral terminology: `Document Fact`, `Interpretation`, `Professional Review Needed`.
- Flagged areas use neutral phrasing: *"This item may require additional facts, jurisdiction-specific analysis, or review by a qualified legal professional."*
- Verification metrics are strictly labeled `evidence_coverage` (percentage of items with mechanically resolved citations), never "legal accuracy" or "lawyer approved".

### 4. Accessibility and Keyboard Navigation
The workspace conforms to WCAG 2.1 AA:
- Tablist uses standard ARIA roles (`role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`, `aria-controls`).
- Full keyboard support for horizontal navigation (Left/Right Arrow, Home/End) and modal management (Escape to dismiss, focus trapping, `aria-modal="true"`).

### 5. Architectural Boundaries
The Understanding Workspace does NOT implement:
- Interactive Q&A / Chat interfaces (reserved for Phase 10).
- Lawyer-Prep Brief generation (reserved for Phase 11).
- Open-ended LLM document summarization or contract rewriting.
- Deadline scheduling, alert notifications, or timeline intelligence.

## Consequences
- Empowers users to inspect, verify, and understand complex legal agreements transparently.
- Eliminates cognitive load by organizing extraction artifacts into purpose-driven views.
- Maintains strict grounding with instant source text inspection for every extracted fact.
- Cleanly separates document inspection from downstream conversational assistance (Phase 10).
