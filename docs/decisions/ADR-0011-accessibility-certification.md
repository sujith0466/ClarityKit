# ADR-0011: Accessibility Hardening & WCAG 2.1 AA Certification

## Status
Accepted (Phase 12)

## Context
ClarityKit is designed to provide evidence-grounded legal document understanding and preparation. To serve all users—including individuals utilizing screen readers, keyboard-only navigation, speech input, or high-contrast settings—the platform requires comprehensive accessibility hardening conforming to **WCAG 2.1 Level AA** without compromising legal-safety principles or frozen domain architectures.

## Decision

1. **Semantic HTML & Landmark Hierarchy**:
   - Establish native HTML landmarks (`<header role="banner">`, `<main id="main-content">`, `<footer role="contentinfo">`, `<nav aria-label="...">`).
   - Eliminate duplicate `<main>` elements by nesting workspace view panels inside accessible `<section>` and `role="tabpanel"` containers.
   - Implement a visible-on-focus `.skip-to-content` link bypassing global navigation.

2. **Universal Focus Management & Visibility**:
   - Apply a universal `:focus-visible` outline (`outline: 2px solid #0284c7; outline-offset: 2px;`) across all interactive controls.
   - For modal dialogs (specifically `SourceInspectorModal`), implement active focus containment (trapping `Tab` / `Shift+Tab`), `Escape` key dismissal, backdrop dismissal, and focus restoration to the opening trigger element upon unmount.

3. **Accessible Tablist Navigation**:
   - Structure `DocumentWorkspace` navigation with `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`, and `role="tabpanel"`.
   - Implement roving tabindex / arrow key navigation (`ArrowLeft`, `ArrowRight`, `Home`, `End`) allowing standard keyboard traversal across document views.

4. **Color-Independence & Non-Text Information**:
   - Ensure all trust tiers (`DOCUMENT_FACT`, `GENERAL_INFORMATION`, `INTERPRETATION`, `PROFESSIONAL_REVIEW_NEEDED`) and safety statuses (`SAFE`, `LIMITED`, `REVIEW_REQUIRED`, `UNSUPPORTED`) are identified by unambiguous textual labels and distinct icons rather than visual color alone.
   - Ensure contrast ratios exceed WCAG 2.1 AA thresholds (≥ 4.5:1 for standard text, ≥ 3:1 for UI components).

5. **Motion, Zoom & Live Regions**:
   - Support `prefers-reduced-motion: reduce` by disabling non-essential transitions and animations globally while preserving functional state.
   - Implement non-disruptive `aria-live="polite"` status announcements during background generation (Q&A analysis, document upload, brief assembly).

6. **Testing & Certification Harness**:
   - Integrate automated `axe-core` accessibility rule assertions into frontend unit tests (`src/accessibility.test.tsx`).
   - Provide a standalone mechanical evaluation harness (`scripts/run_accessibility_eval.py`) certifying CSS, landmarks, ARIA semantics, and automated test execution.
   - Maintain a manual verification checklist (`docs/accessibility-checklist.md`).

## Invariants Preserved
- **NO EVIDENCE → NO DOCUMENT-SPECIFIC CLAIM**: Accessibility changes do not alter claim extraction, mechanical validation, or safety statuses.
- **Trust & Safety Taxonomy**: The 4 trust tiers and 4 safety statuses remain strictly preserved and unmodified.
- **Single Source of Truth**: Reuses Phase 7 `EvidenceValidator`, Phase 8 `TrustClassifier`, Phase 9 `SourceInspectorModal`, Phase 10 `QAService`, and Phase 11 `LawyerPreparationBrief`.

## Consequences
- The frontend interface is usable via keyboard-only and assistive screen reader technologies.
- Continuous accessibility regression prevention is enforced via automated CI quality gates.
