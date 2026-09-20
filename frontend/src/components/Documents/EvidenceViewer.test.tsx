import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EvidenceViewer } from "./EvidenceViewer";
import { DocumentEvidenceReport } from "../../types/evidence";

const mockReport: DocumentEvidenceReport = {
  document_id: "doc-123",
  disclaimer:
    "Citation validity indicates that the referenced text span exists at the claimed document location.",
  generated_at: "2026-09-20T10:00:00Z",
  coverage: {
    total_claims: 3,
    valid_claims: 2,
    invalid_claims: 1,
    unverified_claims: 0,
    coverage_ratio: 0.6667,
    coverage_percentage: 66.67,
    is_fully_covered: false,
  },
  claims: [
    {
      id: "claim-1",
      document_id: "doc-123",
      claim_text: "Party: Acme Corp (Role: Landlord)",
      claim_type: "party",
      validation_status: "VALID",
      evidence: {
        document_id: "doc-123",
        page_start: 1,
        page_end: 1,
        source_span: 'Acme Corp ("Landlord")',
        source_text: 'Acme Corp ("Landlord")',
        match_type: "exact",
        validation_status: "VALID",
      },
    },
    {
      id: "claim-2",
      document_id: "doc-123",
      claim_text: "Obligation: Tenant - Pay rent of $3,500",
      claim_type: "obligation",
      validation_status: "VALID",
      evidence: {
        document_id: "doc-123",
        page_start: 2,
        page_end: 2,
        source_span: "Tenant shall pay monthly rent of $3,500.",
        source_text: "Tenant shall pay monthly rent of $3,500.",
        match_type: "normalized_whitespace",
        validation_status: "VALID",
      },
    },
    {
      id: "claim-3",
      document_id: "doc-123",
      claim_text: "Date: Notice Deadline - 60 days notice",
      claim_type: "date",
      validation_status: "INVALID",
      evidence: {
        document_id: "doc-123",
        page_start: 4,
        page_end: 4,
        source_span: "60 days prior written notice",
        match_type: "unmatched",
        validation_status: "INVALID",
        validation_reason: "SPAN_NOT_FOUND_ON_PAGE",
      },
    },
  ],
};

describe("EvidenceViewer Component", () => {
  it("renders coverage percentage and progress metrics accurately without rounding up", () => {
    render(
      <EvidenceViewer
        report={mockReport}
        documentFilename="lease.pdf"
        onClose={vi.fn()}
      />
    );

    expect(screen.getByTestId("evidence-viewer")).toBeInTheDocument();
    expect(screen.getByText("66.67%")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByTestId("evidence-disclaimer")).toHaveTextContent(
      "Citation validity indicates that the referenced text span exists at the claimed document location."
    );
  });

  it("filters claims by validation status", () => {
    render(
      <EvidenceViewer
        report={mockReport}
        documentFilename="lease.pdf"
        onClose={vi.fn()}
      />
    );

    expect(screen.getAllByRole("feed")[0]).toBeInTheDocument();
    expect(screen.getByTestId("claim-card-claim-1")).toBeInTheDocument();
    expect(screen.getByTestId("claim-card-claim-2")).toBeInTheDocument();
    expect(screen.getByTestId("claim-card-claim-3")).toBeInTheDocument();

    // Select Valid Only
    fireEvent.change(screen.getByTestId("filter-status"), {
      target: { value: "VALID" },
    });

    expect(screen.getByTestId("claim-card-claim-1")).toBeInTheDocument();
    expect(screen.getByTestId("claim-card-claim-2")).toBeInTheDocument();
    expect(screen.queryByTestId("claim-card-claim-3")).not.toBeInTheDocument();

    // Select Invalid Only
    fireEvent.change(screen.getByTestId("filter-status"), {
      target: { value: "INVALID" },
    });

    expect(screen.queryByTestId("claim-card-claim-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("claim-card-claim-2")).not.toBeInTheDocument();
    expect(screen.getByTestId("claim-card-claim-3")).toBeInTheDocument();
  });

  it("filters claims by claim type", () => {
    render(
      <EvidenceViewer
        report={mockReport}
        documentFilename="lease.pdf"
        onClose={vi.fn()}
      />
    );

    fireEvent.change(screen.getByTestId("filter-type"), {
      target: { value: "obligation" },
    });

    expect(screen.queryByTestId("claim-card-claim-1")).not.toBeInTheDocument();
    expect(screen.getByTestId("claim-card-claim-2")).toBeInTheDocument();
    expect(screen.queryByTestId("claim-card-claim-3")).not.toBeInTheDocument();
  });

  it("opens and closes the source inspection modal", () => {
    render(
      <EvidenceViewer
        report={mockReport}
        documentFilename="lease.pdf"
        onClose={vi.fn()}
      />
    );

    const inspectBtn = screen.getByTestId("inspect-btn-claim-1");
    fireEvent.click(inspectBtn);

    expect(screen.getByText("Source Span Inspection")).toBeInTheDocument();
    expect(
      screen.getByText("Authoritative Source Passage:")
    ).toBeInTheDocument();

    const closeBtn = screen.getByTestId("close-source-inspector");
    fireEvent.click(closeBtn);

    expect(
      screen.queryByText("Source Span Inspection")
    ).not.toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const handleClose = vi.fn();
    render(
      <EvidenceViewer
        report={mockReport}
        documentFilename="lease.pdf"
        onClose={handleClose}
      />
    );

    fireEvent.click(screen.getByTestId("close-evidence-viewer-btn"));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("safely escapes and renders malicious injection text", () => {
    const maliciousReport: DocumentEvidenceReport = {
      ...mockReport,
      claims: [
        {
          id: "claim-malicious",
          document_id: "doc-123",
          claim_text: "<script>alert('xss')</script>",
          claim_type: "general_fact",
          validation_status: "VALID",
          evidence: {
            document_id: "doc-123",
            page_start: 1,
            page_end: 1,
            source_span: "<img src=x onerror=alert(1)>",
            source_text: "<img src=x onerror=alert(1)>",
            match_type: "exact",
            validation_status: "VALID",
          },
        },
      ],
    };

    render(
      <EvidenceViewer
        report={maliciousReport}
        documentFilename="xss.pdf"
        onClose={vi.fn()}
      />
    );

    expect(
      screen.getByText("<script>alert('xss')</script>")
    ).toBeInTheDocument();
    expect(
      screen.getByText('"<img src=x onerror=alert(1)>"')
    ).toBeInTheDocument();
  });
});
