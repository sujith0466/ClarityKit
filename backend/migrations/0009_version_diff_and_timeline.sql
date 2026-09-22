-- Migration: 0009_version_diff_and_timeline.sql
-- Description: Creates document_version_diffs and document_timelines tables with strict relational FKs and ON DELETE CASCADE

CREATE TABLE IF NOT EXISTS document_version_diffs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    v1_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    v2_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Version Diff',
    diff_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_version_diffs_user_id
    ON document_version_diffs(user_id);

CREATE INDEX IF NOT EXISTS idx_document_version_diffs_v1_doc
    ON document_version_diffs(v1_document_id);

CREATE INDEX IF NOT EXISTS idx_document_version_diffs_v2_doc
    ON document_version_diffs(v2_document_id);

CREATE TABLE IF NOT EXISTS document_timelines (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Document Timeline',
    timeline_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_timelines_user_id
    ON document_timelines(user_id);

CREATE INDEX IF NOT EXISTS idx_document_timelines_document_id
    ON document_timelines(document_id);
