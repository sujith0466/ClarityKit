export type EvidenceValidationStatus = "VALID" | "INVALID" | "UNVERIFIED";

export type EvidenceMatchType =
  | "exact"
  | "normalized_whitespace"
  | "cross_page"
  | "unmatched";

export type ClaimType =
  | "party"
  | "clause"
  | "obligation"
  | "date"
  | "review_flag"
  | "general_fact";

export interface EvidenceReference {
  readonly document_id: string;
  readonly page_start: number;
  readonly page_end: number;
  readonly source_span: string;
  readonly section?: string | null;
  readonly clause_id?: string | null;
  readonly source_text?: string | null;
  readonly char_start?: number | null;
  readonly char_end?: number | null;
  readonly match_type: EvidenceMatchType;
  readonly validation_status: EvidenceValidationStatus;
  readonly validation_reason?: string | null;
}

export interface Claim {
  readonly id: string;
  readonly document_id: string;
  readonly claim_text: string;
  readonly claim_type: ClaimType;
  readonly entity_id?: string | null;
  readonly evidence?: EvidenceReference | null;
  readonly validation_status: EvidenceValidationStatus;
}

export interface EvidenceCoverage {
  readonly total_claims: number;
  readonly valid_claims: number;
  readonly invalid_claims: number;
  readonly unverified_claims: number;
  readonly coverage_ratio: number;
  readonly coverage_percentage: number;
  readonly is_fully_covered: boolean;
}

export interface DocumentEvidenceReport {
  readonly document_id: string;
  readonly claims: readonly Claim[];
  readonly coverage: EvidenceCoverage;
  readonly generated_at: string;
  readonly disclaimer: string;
}

export interface DocumentEvidenceResponse {
  readonly status: "success" | "error";
  readonly evidence_report: DocumentEvidenceReport;
  readonly message?: string;
}
