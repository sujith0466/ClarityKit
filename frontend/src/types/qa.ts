/**
 * Grounded Document Q&A TypeScript Definitions (Phase 10)
 */

import { EvidenceReference } from "./evidence";

export interface AnswerClaim {
  readonly id: string;
  readonly claim_text: string;
  readonly claim_type: string;
  readonly evidence?: EvidenceReference | null;
  readonly trust_tier: string;
  readonly safety_status: string;
  readonly is_valid: boolean;
  readonly validation_reason?: string;
}

export interface AnswerEvidenceSummary {
  readonly claim_id: string;
  readonly claim_text: string;
  readonly page_start: number;
  readonly page_end: number;
  readonly source_span: string;
}

export interface QAMessage {
  readonly id: string;
  readonly session_id: string;
  readonly document_id: string;
  readonly question_text: string;
  readonly answer_text: string;
  readonly trust_tier: string;
  readonly safety_status: string;
  readonly evidence_coverage: number;
  readonly is_grounded: boolean;
  readonly claims: readonly AnswerClaim[];
  readonly evidence_references: readonly AnswerEvidenceSummary[];
  readonly created_at: string;
}

export interface QASession {
  readonly id: string;
  readonly document_id: string;
  readonly title: string;
  readonly created_at: string;
  readonly updated_at: string;
  readonly messages?: readonly QAMessage[];
}

export interface QARequest {
  readonly question: string;
  readonly session_id?: string;
}
