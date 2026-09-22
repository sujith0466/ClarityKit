import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ComparisonSelector } from "./ComparisonSelector";
import { SideBySideFindingCard } from "./SideBySideFindingCard";
import { ComparisonOverview } from "./ComparisonOverview";
import {
  ComparisonDocumentRef,
  ComparisonFinding,
  ComparisonSummary,
} from "../../types/comparison";
import { DocumentItem } from "../../types/document";

const mockDocuments: DocumentItem[] = [
  {
    id: "doc-1",
    filename: "Lease_2025.pdf",
    content_type: "application/pdf",
    size_bytes: 1024,
    sha256_hash: "h1",
    status: "READY",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "doc-2",
    filename: "Lease_Addendum_2026.pdf",
    content_type: "application/pdf",
    size_bytes: 2048,
    sha256_hash: "h2",
    status: "READY",
    created_at: "2026-02-01T00:00:00Z",
    updated_at: "2026-02-01T00:00:00Z",
  },
  {
    id: "doc-3",
    filename: "Guaranty.pdf",
    content_type: "application/pdf",
    size_bytes: 1500,
    sha256_hash: "h3",
    status: "READY",
    created_at: "2026-03-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];

const mockDocRefs: ComparisonDocumentRef[] = [
  { id: "doc-1", filename: "Lease_2025.pdf", page_count: 5 },
  { id: "doc-2", filename: "Lease_Addendum_2026.pdf", page_count: 3 },
];

const mockFinding: ComparisonFinding = {
  id: "finding-1",
  category: "EFFECTIVE_DATE",
  title: "Effective Date Inconsistency",
  classification: "POTENTIAL_INCONSISTENCY",
  plain_english_explanation:
    "The documents specify conflicting commencement dates.",
  neutral_lawyer_question: "Which commencement date is intended to govern?",
  evidence_by_doc: {
    "doc-1": {
      document_id: "doc-1",
      document_name: "Lease_2025.pdf",
      page_number: 1,
      exact_quote: "January 1, 2026",
      validation_status: "EXACT_MATCH",
      validation_reason: "Exact match in source text",
      match_type: "exact",
    },
    "doc-2": {
      document_id: "doc-2",
      document_name: "Lease_Addendum_2026.pdf",
      page_number: 1,
      exact_quote: "March 1, 2026",
      validation_status: "EXACT_MATCH",
      validation_reason: "Exact match in source text",
      match_type: "exact",
    },
  },
  suggested_next_steps: ["Confirm commencement date with landlord."],
};

const mockSummary: ComparisonSummary = {
  total_findings: 4,
  total_matches: 2,
  total_differences: 1,
  total_inconsistencies: 1,
  total_present_in_one_only: 0,
  total_unresolved: 0,
  category_breakdown: {
    PARTIES: 2,
    EFFECTIVE_DATE: 1,
    NOTICE_PERIOD: 1,
  },
};

describe("Multi-Document Comparison UI Components", () => {
  describe("ComparisonSelector", () => {
    it("renders ready documents and allows selecting 2 to 5 documents", () => {
      const onSelectionChange = vi.fn();
      const onCompare = vi.fn();

      render(
        <ComparisonSelector
          documents={mockDocuments}
          selectedDocIds={["doc-1"]}
          onSelectionChange={onSelectionChange}
          onCompare={onCompare}
          isComparing={false}
        />
      );

      expect(screen.getByText("Multi-Document Comparison")).toBeInTheDocument();
      expect(screen.getByText("Lease_2025.pdf")).toBeInTheDocument();
      expect(screen.getByText("Lease_Addendum_2026.pdf")).toBeInTheDocument();

      // Compare button disabled when < 2 selected
      const compareBtn = screen.getByRole("button", {
        name: /compare 1 documents/i,
      });
      expect(compareBtn).toBeDisabled();

      // Toggle document selection
      const addendumCheckbox = screen.getByLabelText(
        "Select Lease_Addendum_2026.pdf"
      );
      fireEvent.click(addendumCheckbox);

      expect(onSelectionChange).toHaveBeenCalledWith(["doc-1", "doc-2"]);
    });

    it("triggers onCompare with optional title when 2 documents are selected", () => {
      const onSelectionChange = vi.fn();
      const onCompare = vi.fn();

      render(
        <ComparisonSelector
          documents={mockDocuments}
          selectedDocIds={["doc-1", "doc-2"]}
          onSelectionChange={onSelectionChange}
          onCompare={onCompare}
          isComparing={false}
        />
      );

      const titleInput = screen.getByLabelText(/comparison title/i);
      fireEvent.change(titleInput, { target: { value: "Lease vs Addendum" } });

      const compareBtn = screen.getByRole("button", {
        name: /compare 2 documents/i,
      });
      expect(compareBtn).not.toBeDisabled();

      fireEvent.click(compareBtn);
      expect(onCompare).toHaveBeenCalledWith("Lease vs Addendum");
    });
  });

  describe("SideBySideFindingCard", () => {
    it("renders finding details, side-by-side quotes, and lawyer question", () => {
      const onInspect = vi.fn();

      render(
        <SideBySideFindingCard
          finding={mockFinding}
          documents={mockDocRefs}
          onInspect={onInspect}
        />
      );

      expect(
        screen.getByText("Effective Date Inconsistency")
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          "The documents specify conflicting commencement dates."
        )
      ).toBeInTheDocument();
      expect(screen.getByText("Potential Inconsistency")).toBeInTheDocument();

      // Side-by-side evidence quotes
      expect(screen.getByText(/January 1, 2026/)).toBeInTheDocument();
      expect(screen.getByText(/March 1, 2026/)).toBeInTheDocument();

      // Lawyer question
      expect(
        screen.getByText("Which commencement date is intended to govern?")
      ).toBeInTheDocument();

      // Inspect source button click
      const inspectButtons = screen.getAllByRole("button", {
        name: /inspect source text/i,
      });
      expect(inspectButtons.length).toBe(2);

      fireEvent.click(inspectButtons[0]);
      expect(onInspect).toHaveBeenCalledWith(
        expect.objectContaining({
          claimText: "January 1, 2026",
          pageNumber: 1,
          validationStatus: "EXACT_MATCH",
        })
      );
    });
  });

  describe("ComparisonOverview", () => {
    it("renders summary metrics, statutory disclaimer, and filter options", () => {
      const onCategoryChange = vi.fn();
      const onClassificationChange = vi.fn();

      render(
        <ComparisonOverview
          summary={mockSummary}
          activeCategory="ALL"
          onCategoryChange={onCategoryChange}
          activeClassification="ALL"
          onClassificationChange={onClassificationChange}
          disclaimer="Informational Comparison Only — Not Legal Advice."
        />
      );

      expect(
        screen.getByText("Informational Comparison Only — Not Legal Advice.")
      ).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument(); // Total findings
      expect(screen.getByText("2")).toBeInTheDocument(); // Matches
      expect(screen.getAllByText("1").length).toBe(2); // Differences & Inconsistencies

      const categorySelect = screen.getByLabelText(/category:/i);
      fireEvent.change(categorySelect, { target: { value: "EFFECTIVE_DATE" } });
      expect(onCategoryChange).toHaveBeenCalledWith("EFFECTIVE_DATE");

      const classificationSelect = screen.getByLabelText(/classification:/i);
      fireEvent.change(classificationSelect, {
        target: { value: "POTENTIAL_INCONSISTENCY" },
      });
      expect(onClassificationChange).toHaveBeenCalledWith(
        "POTENTIAL_INCONSISTENCY"
      );
    });
  });
});
