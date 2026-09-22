-- Migration: 0008_document_comparisons.sql
-- Description: Creates document_comparisons table for multi-document comparisons with tenant isolation and cascade deletion

CREATE TABLE IF NOT EXISTS document_comparisons (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Document Comparison',
    document_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    comparison_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_comparisons_user_id
    ON document_comparisons(user_id);

CREATE INDEX IF NOT EXISTS idx_document_comparisons_created_at
    ON document_comparisons(created_at);

CREATE INDEX IF NOT EXISTS idx_document_comparisons_document_ids
    ON document_comparisons USING gin (document_ids);
