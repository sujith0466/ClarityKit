import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LawyerBriefView } from "./LawyerBriefView";
import { LawyerPreparationBrief } from "../../types/brief";

// Mock AuthContext
vi.mock("../../context/useAuth", () => ({
  useAuth: () => ({
    token: "mock-jwt-token",
    isAuthenticated: true,
    user: { user_id: "u-123", email: "test@example.com" },
  }),
}));

const mockBrief: LawyerPreparationBrief = {
  id: "brief-123",
  document_id: "doc-123",
  title: "Lawyer-Preparation Brief: Commercial Lease Agreement",
  situation_summary:
    "This brief organizes extracted clauses, obligations, and factual questions from the Commercial Lease Agreement.",
  sections: {
    parties: {
      section_key: "parties",
      title: "Document Snapshot & Parties",
      description: "Identified contracting parties and designated roles.",
      items: [
        {
          id: "item-p1",
          text: "Landlord: Acme Realty LLC",
          title: "Landlord",
          content: "Acme Realty LLC",
          source_type: "PARTY",
          trust_tier: "DOCUMENT_FACT",
          safety_status: "SAFE",
          page_start: 1,
          page_end: 1,
          source_span: "Acme Realty LLC (Landlord)",
        },
      ],
    },
    clauses: {
      section_key: "clauses",
      title: "Key Extracted Clauses & Provisions",
      description:
        "Substantive contract clauses extracted with evidence spans.",
      items: [
        {
          id: "item-c1",
          text: "Tenant shall not assign without prior written consent.",
          title: "Assignment Clause",
          content: "Tenant shall not assign without prior written consent.",
          source_type: "CLAUSE",
          trust_tier: "DOCUMENT_FACT",
          safety_status: "SAFE",
          page_start: 3,
          page_end: 3,
          source_span: "Tenant shall not assign without prior written consent.",
        },
      ],
    },
  },
  questions_for_lawyer: [
    {
      question:
        "What notice period is required for assignment consent under Clause 12?",
      category: "ASSIGNMENT",
      rationale:
        "The agreement requires prior written consent but does not specify a timeline.",
      related_clause_id: "clause-12",
    },
  ],
  facts_to_confirm: ["Confirm exact legal entity name for Tenant."],
  documents_to_bring: ["Executed copy of original lease agreement."],
  open_questions: ["Whether verbal consent was previously discussed."],
  completeness_score: 0.85,
  is_grounded: true,
  disclaimer:
    "This preparation brief is an evidence-grounded aid designed to help you prepare for a consultation with a qualified legal professional.",
  created_at: "2026-09-20T12:00:00Z",
  updated_at: "2026-09-20T12:00:00Z",
};

describe("LawyerBriefView Component", () => {
  const mockOnInspect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no brief has been generated yet", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/brief")) {
        return Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ error: "not_found" }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });
    });

    render(<LawyerBriefView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("brief-empty")).toBeInTheDocument();
    });

    expect(
      screen.getByText("No Lawyer Brief Generated Yet")
    ).toBeInTheDocument();
    expect(screen.getByTestId("generate-brief-btn")).toBeInTheDocument();
  });

  it("generates brief when generate button is clicked", async () => {
    globalThis.fetch = vi
      .fn()
      .mockImplementation((url: string, opts?: RequestInit) => {
        if (url.includes("/brief") && opts?.method === "POST") {
          return Promise.resolve({
            ok: true,
            status: 201,
            json: () =>
              Promise.resolve({ status: "success", brief: mockBrief }),
          });
        }
        if (url.includes("/brief")) {
          return Promise.resolve({
            ok: false,
            status: 404,
            json: () => Promise.resolve({ error: "not_found" }),
          });
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({}),
        });
      });

    render(<LawyerBriefView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("generate-brief-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("generate-brief-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("lawyer-brief-view")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Lawyer-Preparation Brief: Commercial Lease Agreement")
    ).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("renders existing brief with safety notice, questions, checklists, and snapshot sections", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/brief")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ status: "success", brief: mockBrief }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });
    });

    render(<LawyerBriefView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("lawyer-brief-view")).toBeInTheDocument();
    });

    // Check Safety Notice
    expect(
      screen.getByText(/CONSULTATION PREPARATION AID — NOT LEGAL ADVICE/i)
    ).toBeInTheDocument();

    // Check Questions for lawyer
    expect(
      screen.getByText(
        "What notice period is required for assignment consent under Clause 12?"
      )
    ).toBeInTheDocument();

    // Check Facts to confirm
    expect(
      screen.getByText("Confirm exact legal entity name for Tenant.")
    ).toBeInTheDocument();

    // Check Documents to bring
    expect(
      screen.getByText("Executed copy of original lease agreement.")
    ).toBeInTheDocument();

    // Check Snapshot section
    expect(screen.getByTestId("brief-section-clauses")).toBeInTheDocument();
    expect(
      screen.getByText("Tenant shall not assign without prior written consent.")
    ).toBeInTheDocument();
  });

  it("triggers onInspect when Inspect Source is clicked in brief snapshot", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/brief")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ status: "success", brief: mockBrief }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });
    });

    render(<LawyerBriefView documentId="doc-123" onInspect={mockOnInspect} />);

    await waitFor(() => {
      expect(screen.getByTestId("lawyer-brief-view")).toBeInTheDocument();
    });

    const inspectBtn = screen.getByLabelText(
      "Inspect source for Assignment Clause"
    );
    fireEvent.click(inspectBtn);

    expect(mockOnInspect).toHaveBeenCalledTimes(1);
    expect(mockOnInspect).toHaveBeenCalledWith({
      title: "Assignment Clause",
      claimText: "Tenant shall not assign without prior written consent.",
      claimType: "CLAUSE",
      pageStart: 3,
      pageEnd: 3,
      sourceSpan: "Tenant shall not assign without prior written consent.",
      trustTier: "DOCUMENT_FACT",
    });
  });

  it("handles PDF export trigger", async () => {
    // Mock URL.createObjectURL, URL.revokeObjectURL, and HTMLAnchorElement click
    window.URL.createObjectURL = vi.fn(() => "blob:http://localhost/mock-pdf");
    window.URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/export/pdf")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          blob: () =>
            Promise.resolve(
              new Blob(["%PDF-1.4 mock content"], { type: "application/pdf" })
            ),
        });
      }
      if (url.includes("/brief")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ status: "success", brief: mockBrief }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });
    });

    render(
      <LawyerBriefView
        documentId="doc-123"
        documentFilename="lease.pdf"
        onInspect={mockOnInspect}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId("lawyer-brief-view")).toBeInTheDocument();
    });

    const exportBtn = screen.getByLabelText(
      "Export lawyer preparation brief as PDF"
    );
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/briefs/brief-123/export/pdf",
        expect.objectContaining({
          headers: { Authorization: "Bearer mock-jwt-token" },
        })
      );
    });
  });
});
