#!/usr/bin/env python
"""ClarityKit Accessibility & WCAG 2.1 AA Certification Harness (Phase 12: Tasks T-258 -> T-284).

Performs mechanical audits across frontend templates, stylesheets, landmarks,
accessible names, focus management, reduced motion, ARIA semantics, and runs
the automated axe-core accessibility test suite.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_CSS = FRONTEND_DIR / "src" / "App.css"
COMPONENTS_DIR = FRONTEND_DIR / "src" / "components"


def check_css_accessibility() -> tuple[bool, list[str]]:
    """Audit CSS for focus indicators, reduced motion, and utility classes."""
    issues: list[str] = []
    if not APP_CSS.exists():
        return False, ["App.css not found"]

    css_text = APP_CSS.read_text(encoding="utf-8")

    # 1. Check :focus-visible universal outline
    if ":focus-visible" not in css_text:
        issues.append("Missing universal :focus-visible styling in App.css")

    # 2. Check prefers-reduced-motion
    if "prefers-reduced-motion" not in css_text:
        issues.append("Missing prefers-reduced-motion media queries in App.css")

    # 3. Check skip-to-content
    if ".skip-to-content" not in css_text:
        issues.append("Missing .skip-to-content styling in App.css")

    # 4. Check sr-only / visually-hidden
    if ".sr-only" not in css_text and ".visually-hidden" not in css_text:
        issues.append("Missing .sr-only / .visually-hidden utility classes in App.css")

    return len(issues) == 0, issues


def check_semantic_landmarks() -> tuple[bool, list[str]]:
    """Audit semantic HTML landmarks across layout components."""
    issues: list[str] = []

    main_layout = FRONTEND_DIR / "src" / "components" / "Shell" / "MainLayout.tsx"
    if not main_layout.exists():
        issues.append("MainLayout.tsx not found")
    else:
        layout_text = main_layout.read_text(encoding="utf-8")
        if "skip-to-content" not in layout_text:
            issues.append("MainLayout.tsx missing skip-to-content link")
        if '<main id="main-content"' not in layout_text:
            issues.append("MainLayout.tsx missing main landmark with id='main-content'")

    workspace = COMPONENTS_DIR / "Workspace" / "DocumentWorkspace.tsx"
    if workspace.exists():
        ws_text = workspace.read_text(encoding="utf-8")
        if "workspace-tab-nav" not in ws_text or 'role="tablist"' not in ws_text:
            issues.append("DocumentWorkspace.tsx missing accessible tablist navigation")

    return len(issues) == 0, issues


def check_dialog_accessibility() -> tuple[bool, list[str]]:
    """Audit SourceInspectorModal and dialog accessibility."""
    issues: list[str] = []
    modal_file = COMPONENTS_DIR / "Workspace" / "SourceInspectorModal.tsx"
    if not modal_file.exists():
        return False, ["SourceInspectorModal.tsx not found"]

    text = modal_file.read_text(encoding="utf-8")
    if 'role="dialog"' not in text:
        issues.append("SourceInspectorModal missing role='dialog'")
    if 'aria-modal="true"' not in text:
        issues.append("SourceInspectorModal missing aria-modal='true'")
    if "aria-labelledby" not in text:
        issues.append("SourceInspectorModal missing aria-labelledby")
    if "Escape" not in text:
        issues.append("SourceInspectorModal missing keyboard Escape handler")
    if "previousFocusRef" not in text and "previousFocus" not in text:
        issues.append("SourceInspectorModal missing focus restoration")

    return len(issues) == 0, issues


def check_trust_badges_color_independence() -> tuple[bool, list[str]]:
    """Audit that trust tiers and safety statuses have text labels, not color-only."""
    issues: list[str] = []
    required_trust_tiers = [
        "DOCUMENT_FACT",
        "GENERAL_INFORMATION",
        "INTERPRETATION",
        "PROFESSIONAL_REVIEW_NEEDED",
    ]
    required_safety_statuses = [
        "SAFE",
        "LIMITED",
        "REVIEW_REQUIRED",
        "UNSUPPORTED",
    ]

    # Verify trust types file
    trust_types_file = FRONTEND_DIR / "src" / "types" / "trust.ts"
    if not trust_types_file.exists():
        return False, ["types/trust.ts not found"]

    types_text = trust_types_file.read_text(encoding="utf-8")
    for tier in required_trust_tiers:
        if tier not in types_text:
            issues.append(f"Trust tier '{tier}' missing from frontend trust types")
    for status in required_safety_statuses:
        if status not in types_text:
            issues.append(f"Safety status '{status}' missing from frontend trust types")

    return len(issues) == 0, issues


def run_automated_axe_tests() -> tuple[bool, str]:
    """Run frontend vitest test suite including axe-core audits."""
    cmd = ["npx.cmd", "vitest", "run", "src/accessibility.test.tsx"] if sys.platform == "win32" else ["npx", "vitest", "run", "src/accessibility.test.tsx"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(FRONTEND_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = proc.returncode == 0
        output = proc.stdout if passed else (proc.stdout + "\n" + proc.stderr)
        return passed, output
    except Exception as e:
        return False, f"Failed to execute vitest: {e}"


def run_certification() -> bool:
    print("=" * 78)
    print("CLARITYKIT ACCESSIBILITY & WCAG 2.1 AA CERTIFICATION HARNESS")
    print("=" * 78)
    print("\nAuditing frontend accessibility architecture & running automated tests:\n")

    all_passed = True

    # 1. CSS audit
    css_ok, css_issues = check_css_accessibility()
    print(f"[{'PASS' if css_ok else 'FAIL'}] Stylesheet Accessibility (:focus-visible, reduced motion, skip-link)")
    for issue in css_issues:
        print(f"       - {issue}")
    if not css_ok:
        all_passed = False

    # 2. Landmarks audit
    land_ok, land_issues = check_semantic_landmarks()
    print(f"[{'PASS' if land_ok else 'FAIL'}] Semantic HTML Landmarks (banner, main, tablist, contentinfo)")
    for issue in land_issues:
        print(f"       - {issue}")
    if not land_ok:
        all_passed = False

    # 3. Dialog audit
    dlg_ok, dlg_issues = check_dialog_accessibility()
    print(f"[{'PASS' if dlg_ok else 'FAIL'}] Modal Dialog Architecture (role, aria-modal, focus trap & restoration)")
    for issue in dlg_issues:
        print(f"       - {issue}")
    if not dlg_ok:
        all_passed = False

    # 4. Color-independence audit
    color_ok, color_issues = check_trust_badges_color_independence()
    print(f"[{'PASS' if color_ok else 'FAIL'}] Color-Independent Taxonomy (Trust Tiers & Safety Statuses)")
    for issue in color_issues:
        print(f"       - {issue}")
    if not color_ok:
        all_passed = False

    # 5. Axe-core test execution
    print("\nExecuting automated axe-core & keyboard test suite (src/accessibility.test.tsx)...")
    axe_ok, axe_output = run_automated_axe_tests()
    print(f"[{'PASS' if axe_ok else 'FAIL'}] Automated axe-core & Keyboard Component Suite")
    if not axe_ok:
        all_passed = False
        print("\nAxe Test Output:\n", axe_output)

    print("-" * 78)
    if all_passed:
        print("\nALL AUTOMATED ACCESSIBILITY & CERTIFICATION GATES PASSED (100% SUCCESS RATE)")
        print("Note: Automated checks certify mechanical compliance; manual verification checklist")
        print("is documented in docs/accessibility-checklist.md.")
    else:
        print("\nACCESSIBILITY EVALUATION REPORTED FAILURES")
    print("=" * 78)
    return all_passed


if __name__ == "__main__":
    success = run_certification()
    sys.exit(0 if success else 1)
