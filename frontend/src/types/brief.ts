/**
 * Lawyer-Preparation Brief Frontend Types (Phase 11)
 */

import { EvidenceReference } from "./evidence";
import { SafetyStatus, TrustTier } from "./trust";

export type BriefSourceType =
  | "PARTY"
  | "CLAUSE"
  | "OBLIGATION"
  | "DATE"
  | "REVIEW_AREA"
  | "QA_FINDING"
  | "EXTRACTION"
  | "EVIDENCE"
  | "GROUNDED_QA"
  | "USER_INPUT"
  | "SYNTHESIS";

export interface BriefItem {
  readonly id: string;
  readonly text: string;
  readonly title?: string;
  readonly content?: string;
  readonly source_type: BriefSourceType;
  readonly trust_tier: TrustTier;
  readonly safety_status: SafetyStatus;
  readonly category?: string;
  readonly page_start?: number;
  readonly page_end?: number;
  readonly source_span?: string;
  readonly source_id?: string;
  readonly evidence?: EvidenceReference;
  readonly is_valid?: boolean;
  readonly validation_reason?: string;
  readonly notes?: string;
}

export interface BriefSection {
  readonly section_key: string;
  readonly title: string;
  readonly description: string;
  readonly items: readonly BriefItem[];
}

export interface BriefQuestion {
  readonly question: string;
  readonly category: string;
  readonly rationale?: string;
  readonly related_clause_id?: string;
}

export interface LawyerPreparationBrief {
  readonly id: string;
  readonly document_id: string;
  readonly title: string;
  readonly situation_summary: string;
  readonly executive_summary?: string;
  readonly sections: Record<string, BriefSection>;
  readonly questions_for_lawyer: readonly BriefQuestion[];
  readonly facts_to_confirm: readonly string[];
  readonly documents_to_bring: readonly string[];
  readonly open_questions: readonly string[];
  readonly completeness_score: number;
  readonly evidence_references?: readonly Record<string, unknown>[];
  readonly is_grounded: boolean;
  readonly disclaimer: string;
  readonly created_at: string;
  readonly updated_at: string;
}
