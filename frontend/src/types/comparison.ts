/**
 * Multi-Document Comparison Frontend Types (Phase 13: Task T-309)
 */

export type ComparisonCategory =
  | "PARTIES"
  | "EFFECTIVE_DATE"
  | "TERMINATION_DATE"
  | "NOTICE_PERIOD"
  | "FINANCIAL_TERMS"
  | "GOVERNING_LAW"
  | "DISPUTE_RESOLUTION"
  | "CONFIDENTIALITY"
  | "LIABILITY"
  | "CLAUSE_STRUCTURE";

export type DifferenceClassification =
  | "MATCH"
  | "DIFFERENT"
  | "PRESENT_IN_ONE_ONLY"
  | "POTENTIAL_INCONSISTENCY"
  | "UNRESOLVED";

export interface DocumentEvidenceRef {
  readonly document_id: string;
  readonly document_name: string;
  readonly page_number: number;
  readonly exact_quote: string;
  readonly validation_status:
    | "EXACT_MATCH"
    | "NORMALIZED_MATCH"
    | "CROSS_PAGE_MATCH"
    | "UNRESOLVED";
  readonly validation_reason: string;
  readonly match_type: string;
}

export interface ComparisonDocumentRef {
  readonly id: string;
  readonly filename: string;
  readonly content_type?: string;
  readonly created_at?: string;
  readonly page_count?: number;
}

export interface ComparisonFinding {
  readonly id: string;
  readonly category: ComparisonCategory;
  readonly title: string;
  readonly classification: DifferenceClassification;
  readonly plain_english_explanation: string;
  readonly neutral_lawyer_question?: string | null;
  readonly evidence_by_doc: Record<string, DocumentEvidenceRef>;
  readonly suggested_next_steps: readonly string[];
}

export interface ComparisonSummary {
  readonly total_findings: number;
  readonly total_matches: number;
  readonly total_differences: number;
  readonly total_inconsistencies: number;
  readonly total_present_in_one_only: number;
  readonly total_unresolved: number;
  readonly category_breakdown: Record<string, number>;
}

export interface DocumentComparison {
  readonly id: string;
  readonly user_id: string;
  readonly title: string;
  readonly created_at: string;
  readonly documents: readonly ComparisonDocumentRef[];
  readonly findings: readonly ComparisonFinding[];
  readonly summary: ComparisonSummary;
  readonly disclaimer: string;
}

export interface CreateComparisonRequest {
  readonly document_ids: readonly string[];
  readonly title?: string;
}

export interface ComparisonListItem {
  readonly id: string;
  readonly title: string;
  readonly created_at: string;
  readonly document_count: number;
  readonly documents: readonly ComparisonDocumentRef[];
  readonly summary: ComparisonSummary;
}
