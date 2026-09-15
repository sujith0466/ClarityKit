-- ClarityKit Phase 6: Structured Extraction Schema Migration
-- Defines storage for Parties, Clauses, Obligations, Dates, and Review Flags

-- 1. Extracted Parties Table
CREATE TABLE IF NOT EXISTS extracted_parties (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,
    page_number INTEGER NOT NULL,
    source_span TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extracted_parties_document_id ON extracted_parties (document_id);

-- 2. Extracted Clauses Table
CREATE TABLE IF NOT EXISTS extracted_clauses (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    clause_identifier VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    text TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    source_span TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extracted_clauses_document_id ON extracted_clauses (document_id);
CREATE INDEX IF NOT EXISTS idx_extracted_clauses_category ON extracted_clauses (category);

-- 3. Extracted Obligations Table
CREATE TABLE IF NOT EXISTS extracted_obligations (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    clause_id UUID REFERENCES extracted_clauses(id) ON DELETE SET NULL,
    obligor VARCHAR(255) NOT NULL,
    duty TEXT NOT NULL,
    trigger TEXT,
    deadline TEXT,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    source_span TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extracted_obligations_document_id ON extracted_obligations (document_id);
CREATE INDEX IF NOT EXISTS idx_extracted_obligations_clause_id ON extracted_obligations (clause_id);

-- 4. Extracted Dates Table
CREATE TABLE IF NOT EXISTS extracted_dates (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    date_type VARCHAR(100) NOT NULL,
    raw_text VARCHAR(255) NOT NULL,
    normalized_date VARCHAR(50),
    description TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    source_span TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extracted_dates_document_id ON extracted_dates (document_id);
CREATE INDEX IF NOT EXISTS idx_extracted_dates_date_type ON extracted_dates (date_type);

-- 5. Extracted Review Flags Table
CREATE TABLE IF NOT EXISTS extracted_review_flags (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    related_clause_id UUID REFERENCES extracted_clauses(id) ON DELETE SET NULL,
    flag_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL DEFAULT 'medium',
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    source_span TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extracted_review_flags_document_id ON extracted_review_flags (document_id);
CREATE INDEX IF NOT EXISTS idx_extracted_review_flags_flag_type ON extracted_review_flags (flag_type);
CREATE INDEX IF NOT EXISTS idx_extracted_review_flags_severity ON extracted_review_flags (severity);
