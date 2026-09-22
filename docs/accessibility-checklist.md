# ClarityKit Accessibility & WCAG 2.1 AA Compliance Checklist

Target Standard: **WCAG 2.1 Level AA**  
Phase: **Phase 12 — Accessibility & Accessibility Certification**

---

## Verification Methodology Classification

To maintain strict truth-in-testing and prevent false certification claims:
- **`AUTOMATED PASS`**: Verified mechanically by automated axe-core rule engines and Vitest/Testing Library synthetic DOM tests (`src/accessibility.test.tsx`).
- **`STATIC AUDIT PASS`**: Verified deterministically by static code inspection, stylesheet rule analysis (`scripts/run_accessibility_eval.py`), and TypeScript domain type verification.
- **`MANUAL VERIFICATION REQUIRED`**: Requires physical human interactive evaluation with live assistive technologies (JAWS, NVDA, VoiceOver) or physical display hardware settings. *These have not been performed in automated CI and must be conducted during staging/production validation.*

---

## 1. Keyboard Navigation & Interaction

| Check Item | Requirement | Verification Method | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **All Interactive Elements Focusable** | Buttons, links, inputs, and dropdowns can be reached with `Tab` and `Shift+Tab`. | Automated DOM & Code Audit | **AUTOMATED PASS** | Tested in `accessibility.test.tsx` across Auth, DocumentList, Workspace tabs, Q&A composer, and Brief. |
| **No Keyboard Traps** | Focus can always move into and out of every component without getting stuck. | Automated DOM Tests | **AUTOMATED PASS** | Verified in forms, tab panels, and list views. |
| **Keyboard Activation** | Controls activate with `Enter` and/or `Space` as appropriate. | Automated DOM Tests | **AUTOMATED PASS** | Dropzone activates with `Enter`/`Space`; tab buttons trigger on selection. |
| **Tablist Arrow Navigation** | DocumentWorkspace tabs support `ArrowLeft`, `ArrowRight`, `Home`, and `End` roving focus. | Vitest Key Event Tests | **AUTOMATED PASS** | Automated synthetic key tests verify roving tabindex in `accessibility.test.tsx`. |
| **Modal Escape Dismissal** | SourceInspectorModal closes upon pressing `Escape`. | Automated DOM Tests | **AUTOMATED PASS** | Keydown handler tested with synthetic `Escape` event in Vitest. |

---

## 2. Focus Management & Visibility

| Check Item | Requirement | Verification Method | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **Focus Indicator Visibility** | High-contrast `:focus-visible` outline on all focused elements (`outline: 2px solid #0284c7`). | Static CSS Audit | **STATIC AUDIT PASS** | Universal rule present in `App.css` and verified by `run_accessibility_eval.py`. |
| **Skip-to-Content Link** | Visually hidden link appears on first focus and jumps to `<main id="main-content">`. | Static HTML & CSS Audit | **STATIC AUDIT PASS** | Landmark target verified in `MainLayout.tsx` and styling in `App.css`. |
| **Modal Focus Containment** | Focus is constrained within `SourceInspectorModal` while open. | Vitest Focus Trap Tests | **AUTOMATED PASS** | Synthetic tab cycling verified across first and last focusable elements. |
| **Modal Focus Restoration** | Closing `SourceInspectorModal` restores focus to the triggering element. | Vitest Component Tests | **AUTOMATED PASS** | `previousFocusRef` restoration verified in unmount tests. |
| **Non-Disruptive Dynamic Updates** | Content updates (Q&A responses, uploads) do not unexpectedly steal keyboard focus. | Static Code Audit | **STATIC AUDIT PASS** | Polite status regions used instead of assertive focus shifts. |

---

## 3. Screen Reader Usability & Semantic HTML

| Check Item | Requirement | Verification Method | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **Landmark Roles** | Page includes `<header role="banner">`, `<main id="main-content">`, and `<footer role="contentinfo">`. | Axe-Core & HTML Audit | **AUTOMATED PASS** | Zero landmark duplicate or nesting violations reported by axe-core. |
| **Heading Hierarchy** | Logical `<h1>` to `<h3>` progression without skipped levels. | Axe-Core Rules | **AUTOMATED PASS** | Axe-core heading hierarchy rule evaluated with 0 violations. |
| **Accessible Names for Icon Buttons** | Close buttons, inspect buttons, and action buttons have descriptive `aria-label`s. | Axe-Core Rules | **AUTOMATED PASS** | `aria-label` attributes verified on all icon-only buttons. |
| **Decorative Icon Suppression** | Purely visual emojis and icons have `aria-hidden="true"`. | Static Code Audit | **STATIC AUDIT PASS** | Applied to spinners, status dots, and decorative glyphs. |
| **Form Input Label Association** | Every `<input>` and `<textarea>` has an explicit `<label htmlFor="...">`. | Axe-Core Rules | **AUTOMATED PASS** | Tested with axe-core; zero missing label violations. |
| **Error Banner Announcements** | Validation errors have `role="alert"` and are connected via `aria-describedby` / `aria-invalid`. | Axe-Core & DOM Tests | **AUTOMATED PASS** | Verified in LoginForm and RegisterForm. |
| **Live JAWS Screen Reader Session** | Verification of pronunciation and flow using Freedom Scientific JAWS on Windows. | Human Manual Test | **MANUAL VERIFICATION REQUIRED** | **NOT PERFORMED** in automated test environment. Requires live human QA session on Windows with JAWS running. |
| **Live NVDA Screen Reader Session** | Verification of speech synthesis and roving tabindex using NVDA on Windows. | Human Manual Test | **MANUAL VERIFICATION REQUIRED** | **NOT PERFORMED** in automated test environment. Requires live human QA session on Windows with NVDA running. |
| **Live VoiceOver Screen Reader Session** | Verification of gesture and Rotor navigation using VoiceOver on macOS/iOS. | Human Manual Test | **MANUAL VERIFICATION REQUIRED** | **NOT PERFORMED** in automated test environment. Requires live human QA session on Apple hardware. |

---

## 4. Visual Presentation, Color & Motion

| Check Item | Requirement | Verification Method | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **Color Contrast (Text)** | Text achieves at least 4.5:1 contrast ratio against backgrounds. | Axe-Core & Palette Audit | **AUTOMATED PASS** | Standard theme colors (slate `#0f172a`, `#1e293b` on `#ffffff`) pass 4.5:1 ratio. |
| **Color-Independent Status** | Trust tiers, safety statuses, and review flags convey meaning via text labels + icons. | Static Type & DOM Audit | **STATIC AUDIT PASS** | Explicit text values (`DOCUMENT_FACT`, `SAFE`, `REVIEW_REQUIRED`) rendered alongside visual styling. |
| **Reduced Motion Support** | Transitions and animations disable when `prefers-reduced-motion: reduce` is active. | Static CSS Audit | **STATIC AUDIT PASS** | `@media (prefers-reduced-motion: reduce)` resets in `App.css`. |
| **Physical Zoom & Reflow (200% - 400%)** | Multi-browser layout reflow without horizontal scrolling at 400% zoom on physical viewports. | Physical Browser Test | **MANUAL VERIFICATION REQUIRED** | **NOT PERFORMED** in automated headless environment. Responsive styles use relative units, but physical multi-monitor zoom testing is required. |
| **OS High-Contrast Mode** | Verification of visibility in Windows High Contrast / Forced Colors mode. | Physical Display Test | **MANUAL VERIFICATION REQUIRED** | **NOT PERFORMED** in automated CI environment. |

---

## 5. Domain Surfaces Compliance

| Surface | Accessibility Provisions | Automated & Static Status | Live Screen Reader Status |
| :--- | :--- | :---: | :---: |
| **Authentication** | Connected labels, error banners with `role="alert"`, `aria-invalid`, focusable inputs. | **PASS** | `MANUAL VERIFICATION REQUIRED` |
| **Document Upload** | Accessible dropzone with keyboard `Enter`/`Space` activation, `aria-live` upload progress. | **PASS** | `MANUAL VERIFICATION REQUIRED` |
| **Document List** | Semantic `<table>` with `<th scope="col">`, unique descriptive `aria-label`s on action buttons. | **PASS** | `MANUAL VERIFICATION REQUIRED` |
| **Document Workspace** | ARIA `role="tablist"` with arrow key navigation, `role="tabpanel"` associations. | **PASS** | `MANUAL VERIFICATION REQUIRED` |
| **Source Inspector Modal** | `role="dialog"`, `aria-modal="true"`, focus trap, Escape key handling, focus restoration. | **PASS** | `MANUAL VERIFICATION REQUIRED` |
| **Grounded Q&A** | Labeled composer, `aria-live="polite"` status during response generation, keyboard citation badges. | **PASS** | `MANUAL VERIFICATION REQUIRED` |
| **Lawyer Brief View** | Accessible safety banner, completeness `progressbar` with `aria-valuenow`, semantic checklists. | **PASS** | `MANUAL VERIFICATION REQUIRED` |
| **Evidence & Trust Viewers** | Labeled filter dropdowns, text-explicit trust tiers & safety badges, structured claim cards. | **PASS** | `MANUAL VERIFICATION REQUIRED` |

---

## Summary of Verification

- **Automated Axe-Core Audits**: `9 / 9 components verified (0 violations)`
- **Automated Keyboard & DOM Tests**: `76 / 76 frontend tests passed`
- **Static CSS & Semantic Audits**: `100% passed (scripts/run_accessibility_eval.py)`
- **Live Screen Reader Sessions (JAWS / NVDA / VoiceOver)**: `MANUAL VERIFICATION REQUIRED / NOT PERFORMED IN CI`
- **Physical Multi-Browser Zoom / High-Contrast Displays**: `MANUAL VERIFICATION REQUIRED / NOT PERFORMED IN CI`
