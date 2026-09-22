/**
 * Deadline & Obligation Timeline Frontend Types (Phase 14: Task T-336)
 */

export type TimelineDateType =
  | "FIXED_DATE"
  | "RELATIVE_DEADLINE"
  | "DURATION"
  | "UNSPECIFIED";

export type TimelineItemStatus =
  | "EXPLICIT_FACT"
  | "DERIVED"
  | "UNRESOLVED_TRIGGER";

export interface TimelineEvidenceRef {
  readonly document_id: string;
  readonly document_title?: string;
  readonly page_start: number;
  readonly page_end: number;
  readonly source_span: string;
  readonly exact_quote?: string;
  readonly section?: string;
  readonly validation_status?: string;
  readonly char_start?: number;
  readonly char_end?: number;
  readonly trust_tier?: string;
  readonly safety_status?: string;
}

export interface TimelineItem {
  readonly id: string;
  readonly title: string;
  readonly date_type: TimelineDateType;
  readonly item_status: TimelineItemStatus;
  readonly raw_date_text: string;
  readonly calendar_date?: string | null;
  readonly derived_date?: string | null;
  readonly inputs_used: readonly string[];
  readonly party?: string;
  readonly duty_or_event?: string;
  readonly section?: string;
  readonly evidence_references: readonly TimelineEvidenceRef[];
  readonly trust_tier: string;
  readonly safety_status: string;
  readonly notes?: string;
}

export interface TimelineSummary {
  readonly total_items: number;
  readonly fixed_date_count: number;
  readonly derived_count: number;
  readonly relative_deadline_count: number;
  readonly unresolved_trigger_count: number;
  readonly duration_count: number;
}

export interface DocumentTimeline {
  readonly id: string;
  readonly user_id: string;
  readonly document_id: string;
  readonly document_title: string;
  readonly title: string;
  readonly items: readonly TimelineItem[];
  readonly summary: TimelineSummary;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface TimelineListItem {
  readonly id: string;
  readonly user_id: string;
  readonly document_id: string;
  readonly document_title: string;
  readonly title: string;
  readonly summary: TimelineSummary;
  readonly created_at: string;
}
