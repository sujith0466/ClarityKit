/**
 * Frontend Document Understanding Workspace Types (Phase 9)
 */

import { DocumentItem, DocumentPage } from "./document";
import { DocumentUnderstanding } from "./extraction";
import { DocumentEvidenceReport } from "./evidence";
import { DocumentTrustReport } from "./trust";

export type WorkspaceTab =
  | "overview"
  | "qa"
  | "parties"
  | "clauses"
  | "obligations"
  | "dates"
  | "review_areas"
  | "evidence"
  | "trust";

export interface InspectionTarget {
  readonly title: string;
  readonly claimText: string;
  readonly claimType: string;
  readonly pageNumber?: number;
  readonly pageStart?: number;
  readonly pageEnd?: number;
  readonly sourceSpan: string;
  readonly trustTier?: string;
  readonly matchType?: string;
  readonly validationStatus?: string;
}

export interface WorkspaceBundle {
  readonly document: DocumentItem;
  readonly pages: readonly DocumentPage[];
  readonly understanding: DocumentUnderstanding | null;
  readonly evidenceReport: DocumentEvidenceReport | null;
  readonly trustReport: DocumentTrustReport | null;
}
