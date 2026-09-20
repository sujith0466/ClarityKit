-- Migration: 0005_trust_safety.sql
-- Description: Creates document_trust_assessments table with cascade deletion and indices

CREATE TABLE IF NOT EXISTS document_trust_assessments (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    claim_id UUID NOT NULL,
    claim_text TEXT NOT NULL,
    claim_type VARCHAR(64) NOT NULL,
    trust_tier VARCHAR(64) NOT NULL,
    safety_status VARCHAR(64) NOT NULL,
    evidence_required BOOLEAN NOT NULL DEFAULT TRUE,
    evidence_valid BOOLEAN NOT NULL DEFAULT FALSE,
    professional_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    reasoning_summary TEXT NOT NULL DEFAULT '',
    evidence_data JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trust_assessments_doc_id
    ON document_trust_assessments(document_id);

CREATE INDEX IF NOT EXISTS idx_trust_assessments_tier
    ON document_trust_assessments(trust_tier);

CREATE INDEX IF NOT EXISTS idx_trust_assessments_safety
    ON document_trust_assessments(safety_status);
