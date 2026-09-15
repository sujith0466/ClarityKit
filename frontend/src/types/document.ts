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
  | "deleted"
  | "UPLOADING"
  | "QUEUED"
  | "PROCESSING"
  | "READY"
  | "FAILED"
  | "DELETING"
  | "DELETED";

export interface DocumentItem {
  readonly id: string;
  readonly filename: string;
  readonly size_bytes: number;
  readonly content_type: string;
  readonly sha256_hash: string;
  readonly status: DocumentStatus;
  readonly error_message?: string | null;
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

export type ExtractionMethod = "native" | "ocr" | "NATIVE" | "OCR";

export interface DocumentPage {
  readonly page_id: string;
  readonly document_id: string;
  readonly page_number: number;
  readonly text: string;
  readonly extraction_method: ExtractionMethod;
  readonly char_count: number;
  readonly word_count: number;
  readonly ocr_required: boolean;
  readonly processing_duration_ms?: number;
  readonly created_at?: string;
}

export interface ProcessingSummary {
  readonly document_id: string;
  readonly status: DocumentStatus;
  readonly page_count: number;
  readonly ocr_page_count: number;
  readonly native_page_count: number;
  readonly error_message?: string | null;
  readonly updated_at?: string;
}

export interface ProcessDocumentResponse {
  readonly status: "success";
  readonly document_id: string;
  readonly page_count: number;
  readonly pages: readonly DocumentPage[];
}

export interface DocumentPagesResponse {
  readonly status: "success";
  readonly document_id: string;
  readonly count: number;
  readonly pages: readonly DocumentPage[];
}

export interface DocumentProcessingResponse {
  readonly status: "success";
  readonly processing: ProcessingSummary;
}

export interface RetrievalChunk {
  readonly id: string;
  readonly chunk_id: string;
  readonly document_id: string;
  readonly chunk_index: number;
  readonly text: string;
  readonly page_start: number;
  readonly page_end: number;
  readonly source_page_ids: readonly string[];
  readonly char_count: number;
  readonly token_count_est: number;
  readonly content_hash: string;
  readonly has_embedding: boolean;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface RetrievalResult {
  readonly chunk_id: string;
  readonly document_id: string;
  readonly chunk_index: number;
  readonly text: string;
  readonly page_start: number;
  readonly page_end: number;
  readonly similarity: number;
  readonly char_count: number;
  readonly word_count: number;
}

export interface IndexingSummary {
  readonly document_id: string;
  readonly status: "indexed" | "not_indexed";
  readonly chunk_count: number;
  readonly estimated_token_count: number;
  readonly embedding_dimensions: number;
  readonly embedding_model: string;
}

export interface IndexDocumentResponse {
  readonly status: "success";
  readonly document_id: string;
  readonly chunk_count: number;
  readonly chunks: readonly RetrievalChunk[];
}

export interface DocumentChunksResponse {
  readonly status: "success";
  readonly document_id: string;
  readonly count: number;
  readonly chunks: readonly RetrievalChunk[];
}

export interface RetrievalSearchResponse {
  readonly status: "success";
  readonly query: string;
  readonly count: number;
  readonly results: readonly RetrievalResult[];
}
