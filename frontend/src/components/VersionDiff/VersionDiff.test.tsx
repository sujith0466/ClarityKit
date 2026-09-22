import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VersionSelector } from "./VersionSelector";
import { VersionDiffOverview } from "./VersionDiffOverview";
import { SideBySideDiffCard } from "./SideBySideDiffCard";
import {
  VersionDiffFinding,
  VersionDiffSummary,
} from "../../types/versionDiff";
import { DocumentItem } from "../../types/document";

describe("VersionSelector", () => {
  const mockDocs: DocumentItem[] = [
    {
      id: "doc-1",
      filename: "Lease_v1.pdf",
      content_type: "application/pdf",
      size_bytes: 1024,
      sha256_hash: "h1",
      status: "READY",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    {
      id: "doc-2",
      filename: "Lease_v2.pdf",
      content_type: "application/pdf",
      size_bytes: 1024,
      sha256_hash: "h2",
      status: "READY",
      created_at: "2026-01-02T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    },
  ];

  it("renders selectors and disables compare when documents are identical or not selected", () => {
    const onCompare = vi.fn();
    render(
      <VersionSelector
        documents={mockDocs}
        pastDiffs={[]}
        selectedV1Id=""
        selectedV2Id=""
        onSelectV1={() => {}}
        onSelectV2={() => {}}
        onCompare={onCompare}
        onSelectPastDiff={() => {}}
        isComparing={false}
      />
    );

    const compareBtn = screen.getByRole("button", {
      name: /compare versions/i,
    });
    expect(compareBtn).toBeDisabled();
  });

  it("enables compare when two distinct documents are selected", () => {
    const onCompare = vi.fn();
    render(
      <VersionSelector
        documents={mockDocs}
        pastDiffs={[]}
        selectedV1Id="doc-1"
        selectedV2Id="doc-2"
        onSelectV1={() => {}}
        onSelectV2={() => {}}
        onCompare={onCompare}
        isComparing={false}
        onSelectPastDiff={() => {}}
      />
    );

    const compareBtn = screen.getByRole("button", {
      name: /compare versions/i,
    });
    expect(compareBtn).not.toBeDisabled();
    fireEvent.click(compareBtn);
    expect(onCompare).toHaveBeenCalled();
  });
});

describe("VersionDiffOverview", () => {
  const summary: VersionDiffSummary = {
    total_findings: 5,
    added_count: 2,
    removed_count: 1,
    modified_count: 1,
    unchanged_count: 1,
    potential_change_count: 0,
    unresolved_count: 0,
    category_breakdown: { CLAUSES: 3, DATES: 2 },
  };

  it("renders metric cards and filter pills", () => {
    render(
      <VersionDiffOverview
        summary={summary}
        activeCategory="ALL"
        activeClassification="ALL"
        viewMode="side-by-side"
        onSelectCategory={() => {}}
        onSelectClassification={() => {}}
        onToggleViewMode={() => {}}
      />
    );

    expect(screen.getByText("Total Elements")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText(/Added in V2 \(2\)/i)).toBeInTheDocument();
  });
});

describe("SideBySideDiffCard", () => {
  const finding: VersionDiffFinding = {
    id: "f-1",
    category: "NOTICE",
    title: "Notice Period Modified: 30 Days to 60 Days",
    description:
      "Version 2 specifies 60 days notice, whereas Version 1 specified 30 days.",
    classification: "MODIFIED",
    v1_evidence: [
      {
        document_id: "doc-1",
        version_label: "v1",
        page_start: 1,
        page_end: 1,
        source_span: "30 days notice",
        exact_quote: "30 days notice",
      },
    ],
    v2_evidence: [
      {
        document_id: "doc-2",
        version_label: "v2",
        page_start: 1,
        page_end: 1,
        source_span: "60 days notice",
        exact_quote: "60 days notice",
      },
    ],
    lawyer_questions: ["Is the 60 days notice acceptable?"],
    trust_tier: "DOCUMENT_FACT",
    safety_status: "SAFE",
  };

  it("renders two-column evidence and lawyer questions", () => {
    const onInspect = vi.fn();
    render(
      <SideBySideDiffCard
        finding={finding}
        v1Title="Lease_v1.pdf"
        v2Title="Lease_v2.pdf"
        onInspectSource={onInspect}
      />
    );

    expect(
      screen.getByText("Notice Period Modified: 30 Days to 60 Days")
    ).toBeInTheDocument();
    expect(screen.getByText('"30 days notice"')).toBeInTheDocument();
    expect(screen.getByText('"60 days notice"')).toBeInTheDocument();
    expect(
      screen.getByText("Is the 60 days notice acceptable?")
    ).toBeInTheDocument();
  });
});
