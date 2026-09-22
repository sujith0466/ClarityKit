import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TimelineOverview } from "./TimelineOverview";
import { TimelineItemCard } from "./TimelineItemCard";
import { TimelineItem, TimelineSummary } from "../../types/timeline";

describe("TimelineOverview", () => {
  const summary: TimelineSummary = {
    total_items: 4,
    fixed_date_count: 2,
    derived_count: 1,
    relative_deadline_count: 1,
    unresolved_trigger_count: 1,
    duration_count: 0,
  };

  it("renders metric counters correctly", () => {
    render(
      <TimelineOverview
        summary={summary}
        activeStatus="ALL"
        activeDateType="ALL"
        onSelectStatus={() => {}}
        onSelectDateType={() => {}}
      />
    );

    expect(screen.getByText("Total Milestones")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("Fixed Dates")).toBeInTheDocument();
    expect(screen.getByText("Derived Dates")).toBeInTheDocument();
  });
});

describe("TimelineItemCard", () => {
  const explicitItem: TimelineItem = {
    id: "item-1",
    title: "Date: Effective Date",
    date_type: "FIXED_DATE",
    item_status: "EXPLICIT_FACT",
    raw_date_text: "January 15, 2026",
    calendar_date: "2026-01-15",
    inputs_used: [],
    duty_or_event: "Document milestone",
    evidence_references: [
      {
        document_id: "doc-1",
        page_start: 1,
        page_end: 1,
        source_span: "January 15, 2026",
        exact_quote: "Date: January 15, 2026 (Effective Date)",
      },
    ],
    trust_tier: "DOCUMENT_FACT",
    safety_status: "SAFE",
  };

  const derivedItem: TimelineItem = {
    id: "item-2",
    title: "Relative Deadline: Client",
    date_type: "RELATIVE_DEADLINE",
    item_status: "DERIVED",
    raw_date_text: "within 30 days after invoice",
    calendar_date: "2026-02-14",
    derived_date: "2026-02-14",
    inputs_used: [
      "Trigger Date: January 15, 2026 (2026-01-15)",
      "Offset: 30 calendar days",
    ],
    party: "Client",
    duty_or_event: "Pay invoice",
    evidence_references: [
      {
        document_id: "doc-1",
        page_start: 2,
        page_end: 2,
        source_span: "within 30 days after invoice",
        exact_quote: "within 30 days after invoice",
      },
    ],
    trust_tier: "DOCUMENT_FACT",
    safety_status: "SAFE",
  };

  it("renders explicit document fact date item", () => {
    render(<TimelineItemCard item={explicitItem} onInspectSource={() => {}} />);
    expect(screen.getByText("2026-01-15")).toBeInTheDocument();
    expect(screen.getByText("Explicit Document Fact")).toBeInTheDocument();
    expect(screen.getByText("Date: Effective Date")).toBeInTheDocument();
  });

  it("renders derived calculation with inputs transparency", () => {
    render(<TimelineItemCard item={derivedItem} onInspectSource={() => {}} />);
    expect(screen.getByText("2026-02-14")).toBeInTheDocument();
    expect(screen.getByText("Derived Calculation")).toBeInTheDocument();
    expect(
      screen.getByText("Trigger Date: January 15, 2026 (2026-01-15)")
    ).toBeInTheDocument();
  });
});
