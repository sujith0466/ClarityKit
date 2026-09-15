/**
 * Frontend Document Ingestion Types
 */

export type DocumentStatus =
  | "uploading"
  | "queued"
  | "processing"
  | "ready"
  | "failed"
  | "deleting"
  | "deleted";

export interface DocumentItem {
  readonly id: string;
  readonly filename: string;
  readonly size_bytes: number;
  readonly content_type: string;
  readonly sha256_hash: string;
  readonly status: DocumentStatus;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface DocumentUploadResponse {
  readonly status: "success";
  readonly document: DocumentItem;
}

export interface DocumentListResponse {
  readonly status: "success";
  readonly count: number;
  readonly documents: readonly DocumentItem[];
}
