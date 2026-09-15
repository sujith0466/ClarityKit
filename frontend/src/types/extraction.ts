/**
 * Frontend Structured Extraction & Document Understanding Types (Phase 6)
 */

export type ClauseCategory =
  | "confidentiality"
  | "termination"
  | "payment"
  | "liability"
  | "indemnification"
  | "intellectual_property"
  | "non_compete"
  | "non_solicit"
  | "dispute_resolution"
  | "notices"
  | "severability"
  | "representations"
  | "general";

export type DateType =
  | "effective_date"
  | "expiration_date"
  | "renewal_deadline"
  | "payment_due_date"
  | "notice_deadline"
  | "milestone_date"
  | "execution_date";

export type ReviewFlagType =
  | "restrictive_covenant"
  | "renewal_lock_in"
  | "unilateral_discretion"
  | "ambiguous_term"
  | "missing_standard_term"
  | "general_notice";

export interface ExtractedParty {
  readonly id: string;
  readonly document_id: string;
  readonly name: string;
  readonly role: string;
  readonly page_number: number;
  readonly source_span: string;
  readonly created_at: string;
}

export interface ExtractedClause {
  readonly id: string;
  readonly document_id: string;
  readonly clause_identifier: string;
  readonly title: string;
  readonly category: ClauseCategory | string;
  readonly text: string;
  readonly page_start: number;
  readonly page_end: number;
  readonly source_span: string;
  readonly created_at: string;
}

export interface ExtractedObligation {
  readonly id: string;
  readonly document_id: string;
  readonly clause_id?: string | null;
  readonly obligor: string;
  readonly duty: string;
  readonly trigger?: string | null;
  readonly deadline?: string | null;
  readonly page_start: number;
  readonly page_end: number;
  readonly source_span: string;
  readonly created_at: string;
}

export interface ExtractedDate {
  readonly id: string;
  readonly document_id: string;
  readonly date_type: DateType | string;
  readonly raw_text: string;
  readonly normalized_date?: string | null;
  readonly description: string;
  readonly page_number: number;
  readonly source_span: string;
  readonly created_at: string;
}

export interface ExtractedReviewFlag {
  readonly id: string;
  readonly document_id: string;
  readonly related_clause_id?: string | null;
  readonly flag_type: ReviewFlagType | string;
  readonly title: string;
  readonly description: string;
  readonly severity: "low" | "medium" | "high";
  readonly page_start: number;
  readonly page_end: number;
  readonly source_span: string;
  readonly created_at: string;
}

export interface UnderstandingCounts {
  readonly parties: number;
  readonly clauses: number;
  readonly obligations: number;
  readonly dates: number;
  readonly review_flags: number;
}

export interface DocumentUnderstanding {
  readonly document_id: string;
  readonly parties: readonly ExtractedParty[];
  readonly clauses: readonly ExtractedClause[];
  readonly obligations: readonly ExtractedObligation[];
  readonly dates: readonly ExtractedDate[];
  readonly review_flags: readonly ExtractedReviewFlag[];
  readonly provider_info?: Record<string, unknown>;
  readonly extracted_at: string;
  readonly counts?: UnderstandingCounts;
}

export interface DocumentUnderstandingResponse {
  readonly status: "success";
  readonly understanding: DocumentUnderstanding;
}
