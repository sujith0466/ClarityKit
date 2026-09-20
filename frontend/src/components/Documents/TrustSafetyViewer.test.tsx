import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TrustSafetyViewer } from "./TrustSafetyViewer";
import { DocumentTrustReport } from "../../types/trust";

const mockReport: DocumentTrustReport = {
  document_id: "doc-101",
  overall_safety_status: "SAFE",
  evidence_coverage: 0.8571,
  total_claims: 3,
  tier_counts: {
    DOCUMENT_FACT: 1,
    INTERPRETATION: 1,
    PROFESSIONAL_REVIEW_NEEDED: 1,
  },
  limitation_counts: {
    LEGAL_ENFORCEABILITY: 1,
  },
  generated_at: "2026-09-20T11:00:00Z",
  disclaimer: "This platform does not provide legal advice.",
  assessed_claims: [
    {
      id: "ac-1",
      document_id: "doc-101",
      claim_text: "The lease term is 12 months.",
      claim_type: "clause",
      trust_assessment: {
        claim_id: "ac-1",
        trust_tier: "DOCUMENT_FACT",
        safety_status: "SAFE",
        evidence_required: true,
        evidence_valid: true,
        professional_review_required: false,
        limitations: [],
        reasoning_summary: "Directly supported by page 1 text.",
      },
      evidence: [
        {
          document_id: "doc-101",
          page_start: 1,
          page_end: 1,
          source_span: "Term: 12 months",
          match_type: "exact",
          validation_status: "VALID",
        },
      ],
      created_at: "2026-09-20T11:00:00Z",
    },
    {
      id: "ac-2",
      document_id: "doc-101",
      claim_text: "The clause appears to allow subletting with consent.",
      claim_type: "clause",
      trust_assessment: {
        claim_id: "ac-2",
        trust_tier: "INTERPRETATION",
        safety_status: "LIMITED",
        evidence_required: true,
        evidence_valid: true,
        professional_review_required: false,
        limitations: [],
        reasoning_summary: "Interpretation of lease terms.",
      },
      evidence: [],
      created_at: "2026-09-20T11:00:00Z",
    },
    {
      id: "ac-3",
      document_id: "doc-101",
      claim_text: "Is the automatic renewal enforceable in California?",
      claim_type: "review_flag",
      trust_assessment: {
        claim_id: "ac-3",
        trust_tier: "PROFESSIONAL_REVIEW_NEEDED",
        safety_status: "REVIEW_REQUIRED",
        evidence_required: false,
        evidence_valid: false,
        professional_review_required: true,
        limitations: ["LEGAL_ENFORCEABILITY", "MISSING_JURISDICTION"],
        reasoning_summary: "Enforceability depends on statutory law.",
      },
      evidence: [],
      created_at: "2026-09-20T11:00:00Z",
    },
  ],
};

describe("TrustSafetyViewer Component", () => {
  it("renders Trust & Safety assessment header and overall safety status", () => {
    render(
      <TrustSafetyViewer
        report={mockReport}
        documentFilename="residential_lease.pdf"
      />
    );

    expect(screen.getByText(/Trust & Safety Assessment/i)).toBeInTheDocument();
    expect(screen.getByText(/residential_lease\.pdf/i)).toBeInTheDocument();
    expect(screen.getByTestId("overall-safety-badge")).toHaveTextContent(
      /Safe/i
    );
    expect(screen.getByTestId("trust-coverage-text")).toHaveTextContent(
      "85.7%"
    );
  });

  it("displays all claims and filters by tier", () => {
    render(<TrustSafetyViewer report={mockReport} />);

    expect(
      screen.getByText("The lease term is 12 months.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("The clause appears to allow subletting with consent.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Is the automatic renewal enforceable in California?")
    ).toBeInTheDocument();

    // Filter by DOCUMENT_FACT
    const factFilterBtn = screen.getByTestId("filter-tier-document_fact");
    fireEvent.click(factFilterBtn);

    expect(
      screen.getByText("The lease term is 12 months.")
    ).toBeInTheDocument();
    expect(
      screen.queryByText("The clause appears to allow subletting with consent.")
    ).not.toBeInTheDocument();
  });

  it("displays limitation badges for items needing professional review", () => {
    render(<TrustSafetyViewer report={mockReport} />);

    expect(
      screen.getByTestId("limitation-legal_enforceability")
    ).toHaveTextContent(/LEGAL ENFORCEABILITY/i);
  });

  it("opens and closes citation inspection modal", () => {
    render(<TrustSafetyViewer report={mockReport} />);

    const inspectBtn = screen.getByTestId("inspect-evidence-btn-ac-1");
    fireEvent.click(inspectBtn);

    expect(screen.getByText("Citations for Claim")).toBeInTheDocument();
    expect(screen.getByText('"Term: 12 months"')).toBeInTheDocument();

    const closeBtn = screen.getByText("Close");
    fireEvent.click(closeBtn);

    expect(screen.queryByText("Citations for Claim")).not.toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const handleClose = vi.fn();
    render(<TrustSafetyViewer report={mockReport} onClose={handleClose} />);

    const closeViewerBtn = screen.getByTestId("close-trust-viewer-btn");
    fireEvent.click(closeViewerBtn);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
