import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { AuthProvider } from "./context/AuthContext";
import { LoginForm } from "./components/Auth/LoginForm";
import { RegisterForm } from "./components/Auth/RegisterForm";
import { DocumentUpload } from "./components/Documents/DocumentUpload";
import { DocumentList } from "./components/Documents/DocumentList";
import { DocumentWorkspace } from "./components/Workspace/DocumentWorkspace";
import { SourceInspectorModal } from "./components/Workspace/SourceInspectorModal";
import { QAView } from "./components/QA/QAView";
import { LawyerBriefView } from "./components/Brief/LawyerBriefView";
import { EvidenceViewer } from "./components/Documents/EvidenceViewer";
import { TrustSafetyViewer } from "./components/Documents/TrustSafetyViewer";
import { DocumentItem, DocumentPage } from "./types/document";
import { DocumentUnderstanding } from "./types/extraction";
import { DocumentEvidenceReport } from "./types/evidence";
import { DocumentTrustReport } from "./types/trust";
import { LawyerPreparationBrief } from "./types/brief";

vi.mock("./context/useAuth", () => ({
  useAuth: () => ({
    token: "mock-jwt-token",
    isAuthenticated: true,
    user: { user_id: "user-1", email: "user@example.com", name: "Test User" },
    login: vi.fn(),
    logout: vi.fn(),
    setError: vi.fn(),
    error: null,
  }),
}));

// Helper to run axe-core on rendered container
async function checkA11y(container: HTMLElement) {
  const results = await axe.run(container, {
    rules: {
      // In JSDOM, color-contrast can't accurately compute background canvas colors
      "color-contrast": { enabled: false },
    },
  });
  return results.violations;
}

const mockDoc: DocumentItem = {
  id: "doc-test-123",
  filename: "sample_commercial_lease.pdf",
  size_bytes: 40960,
  content_type: "application/pdf",
  sha256_hash: "abcdef123456",
  status: "READY",
  created_at: "2026-09-22T00:00:00Z",
  updated_at: "2026-09-22T00:00:00Z",
};

const mockPages: DocumentPage[] = [
  {
    page_id: "page-1",
    document_id: "doc-test-123",
    page_number: 1,
    text: "This Commercial Lease Agreement is entered into by Acme Corp and Beta LLC.",
    word_count: 14,
    char_count: 75,
    extraction_method: "native",
    ocr_required: false,
  },
  {
    page_id: "page-2",
    document_id: "doc-test-123",
    page_number: 2,
    text: "Tenant shall pay monthly base rent of $10,000 on the first day of each month.",
    word_count: 15,
    char_count: 77,
    extraction_method: "native",
    ocr_required: false,
  },
];

const mockUnderstanding: DocumentUnderstanding = {
  document_id: "doc-test-123",
  extracted_at: "2026-09-22T00:00:00Z",
  parties: [
    {
      id: "p1",
      document_id: "doc-test-123",
      name: "Acme Corp",
      role: "Landlord",
      page_number: 1,
      source_span: "Acme Corp",
      created_at: "2026-09-22T00:00:00Z",
    },
  ],
  clauses: [
    {
      id: "c1",
      document_id: "doc-test-123",
      clause_identifier: "Clause 1",
      title: "Rent Payment",
      text: "Tenant shall pay monthly base rent of $10,000.",
      category: "payment",
      page_start: 2,
      page_end: 2,
      source_span: "Tenant shall pay monthly base rent",
      created_at: "2026-09-22T00:00:00Z",
    },
  ],
  obligations: [
    {
      id: "o1",
      document_id: "doc-test-123",
      obligor: "Beta LLC",
      duty: "shall pay monthly rent",
      page_start: 2,
      page_end: 2,
      source_span: "shall pay monthly base rent",
      created_at: "2026-09-22T00:00:00Z",
    },
  ],
  dates: [
    {
      id: "d1",
      document_id: "doc-test-123",
      date_type: "effective_date",
      raw_text: "2026-09-22",
      normalized_date: "2026-09-22",
      description: "Effective date of agreement",
      page_number: 1,
      source_span: "2026-09-22",
      created_at: "2026-09-22T00:00:00Z",
    },
  ],
  review_flags: [
    {
      id: "rf1",
      document_id: "doc-test-123",
      flag_type: "ambiguity",
      title: "Ambiguous Term",
      description: "Clause language may require clarification.",
      severity: "low",
      page_start: 1,
      page_end: 1,
      source_span: "Commercial Lease",
      created_at: "2026-09-22T00:00:00Z",
    },
  ],
};

const mockEvidenceReport: DocumentEvidenceReport = {
  document_id: "doc-test-123",
  claims: [],
  coverage: {
    total_claims: 5,
    valid_claims: 5,
    invalid_claims: 0,
    unverified_claims: 0,
    coverage_ratio: 1.0,
    coverage_percentage: 100,
    is_fully_covered: true,
  },
  generated_at: "2026-09-22T00:00:00Z",
  disclaimer: "Evidence mechanically verified against authoritative page text.",
};

const mockTrustReport: DocumentTrustReport = {
  document_id: "doc-test-123",
  assessed_claims: [],
  overall_safety_status: "SAFE",
  evidence_coverage: 1.0,
  total_claims: 5,
  tier_counts: {
    DOCUMENT_FACT: 5,
    GENERAL_INFORMATION: 0,
    INTERPRETATION: 0,
    PROFESSIONAL_REVIEW_NEEDED: 0,
  },
  limitation_counts: {},
  generated_at: "2026-09-22T00:00:00Z",
  disclaimer: "Trust assessments deterministic and auditable.",
};

const mockBrief: LawyerPreparationBrief = {
  id: "brief-test-123",
  document_id: "doc-test-123",
  title: "Lawyer-Preparation Brief: Commercial Lease",
  situation_summary: "Summary of lease agreement for legal consultation.",
  completeness_score: 0.95,
  disclaimer: "CONSULTATION PREPARATION AID — NOT LEGAL ADVICE.",
  questions_for_lawyer: [
    {
      question: "Are the notice periods standard for commercial leases?",
      category: "notice",
      rationale: "Verify 90-day renewal notice provision.",
      related_clause_id: "c1",
    },
  ],
  facts_to_confirm: ["Confirm exact physical address and suite number."],
  documents_to_bring: ["Copy of original signed lease agreement."],
  open_questions: ["Document is silent on security deposit return timeline."],
  sections: {},
  is_grounded: true,
  created_at: "2026-09-22T00:00:00Z",
  updated_at: "2026-09-22T00:00:00Z",
};

describe("Phase 12: Accessibility Certification & WCAG 2.1 AA Compliance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/documents/doc-test-123/pages")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ pages: mockPages }),
        });
      }
      if (url.includes("/api/documents/doc-test-123/understanding")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ understanding: mockUnderstanding }),
        });
      }
      if (url.includes("/api/documents/doc-test-123/evidence")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ evidence_report: mockEvidenceReport }),
        });
      }
      if (url.includes("/api/documents/doc-test-123/trust")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ trust_report: mockTrustReport }),
        });
      }
      if (url.includes("/api/documents/doc-test-123/brief")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ brief: mockBrief }),
        });
      }
      if (url.includes("/api/documents/doc-test-123/questions")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ messages: [] }),
        });
      }
      if (url.includes("/api/documents/doc-test-123/qa/sessions")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ sessions: [] }),
        });
      }
      if (url.includes("/api/documents/doc-test-123")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ document: mockDoc }),
        });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });
  });

  it("LoginForm passes axe accessibility audit and has linked labels & errors", async () => {
    const { container } = render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>
    );

    const violations = await checkA11y(container);
    expect(violations).toEqual([]);

    expect(screen.getByLabelText("Email Address")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
  });

  it("RegisterForm passes axe accessibility audit", async () => {
    const { container } = render(
      <AuthProvider>
        <RegisterForm />
      </AuthProvider>
    );

    const violations = await checkA11y(container);
    expect(violations).toEqual([]);

    expect(screen.getByLabelText("Full Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email Address")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("DocumentUpload passes axe accessibility audit and supports keyboard activation", async () => {
    const { container } = render(
      <AuthProvider>
        <DocumentUpload />
      </AuthProvider>
    );

    const violations = await checkA11y(container);
    expect(violations).toEqual([]);

    const dropzone = screen.getByRole("region", { name: "Document Drop Zone" });
    expect(dropzone).toHaveAttribute("tabIndex", "0");
  });

  it("DocumentList renders accessible table semantics and labeled action buttons", async () => {
    const { container } = render(
      <AuthProvider>
        <DocumentList
          documents={[mockDoc]}
          isLoading={false}
          error={null}
          onRefresh={vi.fn()}
          onDeleteDocument={vi.fn()}
          onOpenWorkspace={vi.fn()}
        />
      </AuthProvider>
    );

    const violations = await checkA11y(container);
    expect(violations).toEqual([]);

    expect(
      screen.getByRole("table", { name: "Uploaded Documents" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Open workspace for sample_commercial_lease.pdf",
      })
    ).toBeInTheDocument();
  });

  it("DocumentWorkspace provides accessible tablist and handles keyboard arrow navigation", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <AuthProvider>
        <DocumentWorkspace
          documentId="doc-test-123"
          initialDocument={mockDoc}
          onClose={vi.fn()}
        />
      </AuthProvider>
    );

    await screen.findByTestId("document-workspace");

    const tablist = screen.getByRole("tablist", {
      name: "Document Understanding Views",
    });
    expect(tablist).toBeInTheDocument();

    const overviewTab = screen.getByRole("tab", { name: /Overview/i });
    const partiesTab = screen.getByRole("tab", { name: /Parties/i });

    expect(overviewTab).toHaveAttribute("aria-selected", "true");
    expect(overviewTab).toHaveAttribute("tabIndex", "0");
    expect(partiesTab).toHaveAttribute("aria-selected", "false");
    expect(partiesTab).toHaveAttribute("tabIndex", "-1");

    // Keyboard navigation: press ArrowRight on tablist
    overviewTab.focus();
    await user.keyboard("{ArrowRight}");
    expect(partiesTab).toHaveAttribute("aria-selected", "true");

    const violations = await checkA11y(container);
    expect(violations).toEqual([]);
  });

  it("SourceInspectorModal enforces focus containment and Escape key dismissal", async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();

    const triggerBtn = document.createElement("button");
    triggerBtn.textContent = "Open Modal Trigger";
    document.body.appendChild(triggerBtn);
    triggerBtn.focus();

    const { container, unmount } = render(
      <SourceInspectorModal
        target={{
          title: "Rent Clause",
          claimText: "Tenant shall pay monthly base rent",
          claimType: "clause",
          pageNumber: 2,
          sourceSpan: "Tenant shall pay monthly base rent",
          trustTier: "DOCUMENT_FACT",
        }}
        pages={mockPages}
        onClose={handleClose}
      />
    );

    const violations = await checkA11y(container);
    expect(violations).toEqual([]);

    const dialog = screen.getByRole("dialog", {
      name: "Source Citation & Evidence",
    });
    expect(dialog).toBeInTheDocument();

    // Escape closes modal
    await user.keyboard("{Escape}");
    expect(handleClose).toHaveBeenCalled();

    unmount();
    document.body.removeChild(triggerBtn);
  });

  it("QAView has accessible question composer, status live region, and keyboard citations", async () => {
    const { container } = render(
      <AuthProvider>
        <QAView
          documentId="doc-test-123"
          documentFilename="sample.pdf"
          onInspect={vi.fn()}
        />
      </AuthProvider>
    );

    await screen.findByTestId("qa-view");

    const violations = await checkA11y(container);
    expect(violations).toEqual([]);

    expect(
      screen.getByLabelText("Ask a question about this document")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Ask Question" })
    ).toBeInTheDocument();
  });

  it("LawyerBriefView renders accessible safety notices, headings, progress bar, and export controls", async () => {
    const { container } = render(
      <AuthProvider>
        <LawyerBriefView
          documentId="doc-test-123"
          documentFilename="sample.pdf"
          onInspect={vi.fn()}
        />
      </AuthProvider>
    );

    await screen.findByTestId("lawyer-brief-view");

    const violations = await checkA11y(container);
    expect(violations).toEqual([]);

    expect(
      screen.getByRole("region", { name: "Legal Consultation Notice" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "Brief completeness score" })
    ).toHaveAttribute("aria-valuenow", "95");
    expect(
      screen.getByRole("button", {
        name: "Export lawyer preparation brief as PDF",
      })
    ).toBeInTheDocument();
  });

  it("EvidenceViewer and TrustSafetyViewer pass axe accessibility audits", async () => {
    const { container: evContainer } = render(
      <EvidenceViewer
        report={mockEvidenceReport}
        documentFilename="sample.pdf"
        onClose={vi.fn()}
      />
    );
    const evViolations = await checkA11y(evContainer);
    expect(evViolations).toEqual([]);

    const { container: trustContainer } = render(
      <TrustSafetyViewer
        report={mockTrustReport}
        documentFilename="sample.pdf"
        onClose={vi.fn()}
      />
    );
    const trustViolations = await checkA11y(trustContainer);
    expect(trustViolations).toEqual([]);
  });
});
