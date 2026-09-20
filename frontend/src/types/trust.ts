import { ClaimType, EvidenceReference } from "./evidence";

export type TrustTier =
  | "DOCUMENT_FACT"
  | "GENERAL_INFORMATION"
  | "INTERPRETATION"
  | "PROFESSIONAL_REVIEW_NEEDED";

export type SafetyStatus =
  | "SAFE"
  | "LIMITED"
  | "REVIEW_REQUIRED"
  | "UNSUPPORTED";

export type LimitationType =
  | "MISSING_EVIDENCE"
  | "INVALID_EVIDENCE"
  | "STALE_EVIDENCE"
  | "CROSS_DOCUMENT_EVIDENCE"
  | "MISSING_JURISDICTION"
  | "MISSING_FACTS"
  | "CURRENT_LAW_REQUIRED"
  | "AMBIGUOUS_LANGUAGE"
  | "OUTSIDE_DOCUMENT"
  | "LEGAL_ENFORCEABILITY"
  | "PROFESSIONAL_JUDGMENT";

export interface TrustAssessment {
  claim_id: string;
  trust_tier: TrustTier;
  safety_status: SafetyStatus;
  evidence_required: boolean;
  evidence_valid: boolean;
  professional_review_required: boolean;
  limitations: LimitationType[];
  reasoning_summary: string;
}

export interface AssessedClaim {
  id: string;
  document_id: string;
  claim_text: string;
  claim_type: ClaimType;
  trust_assessment: TrustAssessment;
  evidence: EvidenceReference[];
  created_at: string;
}

export interface DocumentTrustReport {
  document_id: string;
  assessed_claims: AssessedClaim[];
  overall_safety_status: SafetyStatus;
  evidence_coverage: number;
  total_claims: number;
  tier_counts: Record<string, number>;
  limitation_counts: Record<string, number>;
  generated_at: string;
  disclaimer: string;
}

export interface TrustResponse {
  status: string;
  trust_report: DocumentTrustReport;
}
