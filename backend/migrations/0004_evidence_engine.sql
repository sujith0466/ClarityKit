-- ClarityKit Phase 7: Evidence Engine Schema Migration
-- Defines storage for mechanical evidence records, verification status, and coverage metrics

CREATE TABLE IF NOT EXISTS document_evidence_records (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    claim_id UUID NOT NULL,
    claim_type VARCHAR(50) NOT NULL,
    claim_text TEXT NOT NULL,
    entity_id UUID,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    source_span TEXT NOT NULL,
    source_text TEXT,
    char_start INTEGER,
    char_end INTEGER,
    match_type VARCHAR(50) NOT NULL,
    validation_status VARCHAR(50) NOT NULL,
    validation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_records_document_id ON document_evidence_records (document_id);
CREATE INDEX IF NOT EXISTS idx_evidence_records_validation_status ON document_evidence_records (validation_status);
CREATE INDEX IF NOT EXISTS idx_evidence_records_claim_type ON document_evidence_records (claim_type);
