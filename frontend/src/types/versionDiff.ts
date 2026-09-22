/**
 * Document Version Diff Frontend Types (Phase 14: Task T-336)
 */

export type VersionDiffCategory =
  | "PARTIES"
  | "DATES"
  | "OBLIGATIONS"
  | "CLAUSES"
  | "NOTICE"
  | "GENERAL";

export type VersionDiffClassification =
  | "ADDED"
  | "REMOVED"
  | "MODIFIED"
  | "UNCHANGED"
  | "POTENTIAL_CHANGE"
  | "UNRESOLVED";

export interface VersionEvidenceRef {
  readonly document_id: string;
  readonly version_label: string; // "v1" or "v2"
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

export interface VersionDocumentRef {
  readonly id: string;
  readonly filename: string;
  readonly version_label: string; // "Version 1 (Base)" or "Version 2 (Revised)"
}

export interface VersionDiffFinding {
  readonly id: string;
  readonly category: VersionDiffCategory;
  readonly title: string;
  readonly description: string;
  readonly classification: VersionDiffClassification;
  readonly v1_evidence: readonly VersionEvidenceRef[];
  readonly v2_evidence: readonly VersionEvidenceRef[];
  readonly lawyer_questions: readonly string[];
  readonly trust_tier: string;
  readonly safety_status: string;
}

export interface VersionDiffSummary {
  readonly total_findings: number;
  readonly added_count: number;
  readonly removed_count: number;
  readonly modified_count: number;
  readonly unchanged_count: number;
  readonly potential_change_count: number;
  readonly unresolved_count: number;
  readonly category_breakdown: Record<string, number>;
}

export interface DocumentVersionDiff {
  readonly id: string;
  readonly user_id: string;
  readonly title: string;
  readonly v1_document: VersionDocumentRef;
  readonly v2_document: VersionDocumentRef;
  readonly findings: readonly VersionDiffFinding[];
  readonly summary: VersionDiffSummary;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface CreateVersionDiffRequest {
  readonly v1_document_id: string;
  readonly v2_document_id: string;
  readonly title?: string;
}

export interface VersionDiffListItem {
  readonly id: string;
  readonly user_id: string;
  readonly title: string;
  readonly v1_document: VersionDocumentRef;
  readonly v2_document: VersionDocumentRef;
  readonly summary: VersionDiffSummary;
  readonly created_at: string;
}
