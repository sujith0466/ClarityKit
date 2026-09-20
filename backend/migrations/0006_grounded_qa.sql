-- Migration: 0006_grounded_qa.sql
-- Description: Creates qa_sessions and qa_messages tables with cascade deletion and indices

CREATE TABLE IF NOT EXISTS qa_sessions (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Document Q&A Session',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qa_sessions_doc_id
    ON qa_sessions(document_id);

CREATE TABLE IF NOT EXISTS qa_messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES qa_sessions(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    trust_tier VARCHAR(64) NOT NULL,
    safety_status VARCHAR(64) NOT NULL,
    evidence_coverage FLOAT NOT NULL DEFAULT 0.0,
    is_grounded BOOLEAN NOT NULL DEFAULT FALSE,
    claims JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qa_messages_doc_id
    ON qa_messages(document_id);

CREATE INDEX IF NOT EXISTS idx_qa_messages_session_id
    ON qa_messages(session_id);

CREATE INDEX IF NOT EXISTS idx_qa_messages_trust_tier
    ON qa_messages(trust_tier);
