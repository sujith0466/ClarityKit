-- Migration: 0007_lawyer_preparation_brief.sql
-- Description: Creates preparation_briefs table for structured lawyer-preparation briefs with cascade deletion and indices

CREATE TABLE IF NOT EXISTS preparation_briefs (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Lawyer-Preparation Brief',
    situation_summary TEXT NOT NULL DEFAULT '',
    sections JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_grounded BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_preparation_briefs_doc_id
    ON preparation_briefs(document_id);

CREATE INDEX IF NOT EXISTS idx_preparation_briefs_created_at
    ON preparation_briefs(created_at);
