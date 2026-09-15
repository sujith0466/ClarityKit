import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DocumentUnderstandingView } from "./DocumentUnderstandingView";
import { DocumentUnderstanding } from "../../types/extraction";

const mockUnderstanding: DocumentUnderstanding = {
  document_id: "doc-test-123",
  extracted_at: "2026-09-15T12:00:00Z",
  parties: [
    {
      id: "p-1",
      document_id: "doc-test-123",
      name: "Acme Holdings LLC",
      role: "Landlord",
      page_number: 1,
      source_span: "between Acme Holdings LLC (Landlord)",
      created_at: "2026-09-15T12:00:00Z",
    },
    {
      id: "p-2",
      document_id: "doc-test-123",
      name: "Jane Doe",
      role: "Tenant",
      page_number: 1,
      source_span: "and Jane Doe (Tenant)",
      created_at: "2026-09-15T12:00:00Z",
    },
  ],
  clauses: [
    {
      id: "c-1",
      document_id: "doc-test-123",
      clause_identifier: "Clause-1",
      title: "Payment of Rent",
      category: "payment",
      text: "Tenant shall pay rent of $2,000 monthly.",
      page_start: 1,
      page_end: 1,
      source_span: "1. Payment of Rent",
      created_at: "2026-09-15T12:00:00Z",
    },
  ],
  obligations: [
    {
      id: "o-1",
      document_id: "doc-test-123",
      clause_id: "c-1",
      obligor: "Tenant",
      duty: "shall pay rent of $2,000 monthly",
      trigger: "Monthly on the 1st",
      deadline: "on or before the 1st",
      page_start: 1,
      page_end: 1,
      source_span:
        "Tenant shall pay rent of $2,000 monthly on or before the 1st.",
      created_at: "2026-09-15T12:00:00Z",
    },
  ],
  dates: [
    {
      id: "d-1",
      document_id: "doc-test-123",
      date_type: "effective_date",
      raw_text: "January 15, 2026",
      normalized_date: "2026-01-15",
      description: "Agreement effective date",
      page_number: 1,
      source_span: "Effective Date: January 15, 2026",
      created_at: "2026-09-15T12:00:00Z",
    },
  ],
  review_flags: [
    {
      id: "f-1",
      document_id: "doc-test-123",
      related_clause_id: "c-1",
      flag_type: "renewal_lock_in",
      title: "Automatic Renewal Provision",
      description: "Notice period of 90 days required to prevent auto-renewal.",
      severity: "medium",
      page_start: 2,
      page_end: 2,
      source_span: "This lease will automatically renew...",
      created_at: "2026-09-15T12:00:00Z",
    },
  ],
  counts: {
    parties: 2,
    clauses: 1,
    obligations: 1,
    dates: 1,
    review_flags: 1,
  },
};

describe("DocumentUnderstandingView Component", () => {
  it("renders header, document filename, and initial parties tab", () => {
    const handleClose = vi.fn();
    render(
      <DocumentUnderstandingView
        understanding={mockUnderstanding}
        documentFilename="Commercial_Lease.pdf"
        onClose={handleClose}
      />
    );

    expect(
      screen.getByText(/Structured Understanding: Commercial_Lease.pdf/i)
    ).toBeInTheDocument();
    expect(screen.getByText("Acme Holdings LLC")).toBeInTheDocument();
    expect(screen.getByText("Landlord")).toBeInTheDocument();
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("Tenant")).toBeInTheDocument();
  });

  it("switches tabs to Clauses and displays categorized clause cards", () => {
    render(
      <DocumentUnderstandingView
        understanding={mockUnderstanding}
        onClose={vi.fn()}
      />
    );

    const clausesTab = screen.getByRole("tab", { name: /Clauses/i });
    fireEvent.click(clausesTab);

    expect(screen.getByText(/Payment of Rent/i)).toBeInTheDocument();
    expect(screen.getByText("payment")).toBeInTheDocument();
    expect(
      screen.getByText("Tenant shall pay rent of $2,000 monthly.")
    ).toBeInTheDocument();
  });

  it("switches tabs to Obligations and displays duties and deadlines", () => {
    render(
      <DocumentUnderstandingView
        understanding={mockUnderstanding}
        onClose={vi.fn()}
      />
    );

    const obligationsTab = screen.getByRole("tab", { name: /Obligations/i });
    fireEvent.click(obligationsTab);

    expect(
      screen.getByText("shall pay rent of $2,000 monthly")
    ).toBeInTheDocument();
    expect(screen.getByText(/Due: on or before the 1st/i)).toBeInTheDocument();
  });

  it("switches tabs to Dates and displays normalized ISO tags", () => {
    render(
      <DocumentUnderstandingView
        understanding={mockUnderstanding}
        onClose={vi.fn()}
      />
    );

    const datesTab = screen.getByRole("tab", { name: /Dates/i });
    fireEvent.click(datesTab);

    expect(screen.getByText("January 15, 2026")).toBeInTheDocument();
    expect(screen.getByText("ISO: 2026-01-15")).toBeInTheDocument();
    expect(screen.getByText("Agreement effective date")).toBeInTheDocument();
  });

  it("switches tabs to Review Flags and displays advisory warning banner", () => {
    render(
      <DocumentUnderstandingView
        understanding={mockUnderstanding}
        onClose={vi.fn()}
      />
    );

    const flagsTab = screen.getByRole("tab", { name: /Review Flags/i });
    fireEvent.click(flagsTab);

    expect(
      screen.getByText(/Automatic Renewal Provision/i)
    ).toBeInTheDocument();
    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
    expect(
      screen.getByText(/ClarityKit provides neutral structural extraction/i)
    ).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const handleClose = vi.fn();
    render(
      <DocumentUnderstandingView
        understanding={mockUnderstanding}
        onClose={handleClose}
      />
    );

    const closeBtn = screen.getByRole("button", {
      name: /Close structured understanding view/i,
    });
    fireEvent.click(closeBtn);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("renders empty state messages when understanding entities are empty", () => {
    const emptyUnderstanding: DocumentUnderstanding = {
      document_id: "doc-empty",
      extracted_at: "2026-09-15T12:00:00Z",
      parties: [],
      clauses: [],
      obligations: [],
      dates: [],
      review_flags: [],
    };

    render(
      <DocumentUnderstandingView
        understanding={emptyUnderstanding}
        onClose={vi.fn()}
      />
    );

    expect(
      screen.getByText(/No legal parties identified in document/i)
    ).toBeInTheDocument();
  });
});
