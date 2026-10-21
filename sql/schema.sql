-- Personal Health Record Organizer Database Schema
-- Compatible with Neon Postgres / PostgreSQL 14+

-- Enable uuid generation if available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. runs table: Orchestration and patient run metadata
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_name TEXT NOT NULL,
    patient_id TEXT,
    patient_key TEXT NOT NULL,
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    labs TEXT[] NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, fetching, extracting_checking, waiting_approval, storing, completed, failed
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runs_patient_key ON runs(patient_key);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC);

-- 2. candidates table: Downloaded files and staging area
CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    lab TEXT NOT NULL,
    filename TEXT NOT NULL,
    source_url TEXT,
    listing_title TEXT,
    portal_report_id TEXT,
    portal_date DATE,
    
    -- Download evidence
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    http_status INT DEFAULT 200,
    content_type TEXT,
    file_bytes BYTEA,
    size_bytes BIGINT,
    sha256 TEXT,
    
    -- Extraction
    extract_ok BOOLEAN,
    extract_note TEXT,
    extract_source TEXT, -- 'regex', 'llm', 'failed'
    x_name TEXT,
    x_patient_id TEXT,
    x_report_id TEXT,
    x_date DATE,
    x_test TEXT,
    
    -- Check results
    legit_result JSONB,
    duplicate_result JSONB,
    decision TEXT, -- 'keep', 'duplicate', 'exclude', 'reject', 'needs_review'
    decision_reason TEXT,
    
    -- Final state
    status TEXT NOT NULL DEFAULT 'staging', -- 'staging', 'stored', 'not_stored'
    recheck_ok BOOLEAN,
    recheck_note TEXT,
    
    CONSTRAINT uq_run_lab_filename UNIQUE (run_id, lab, filename)
);

CREATE INDEX IF NOT EXISTS idx_candidates_run_id ON candidates(run_id);
CREATE INDEX IF NOT EXISTS idx_candidates_decision ON candidates(decision);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_sha256 ON candidates(sha256);

-- 3. reports table: The permanent medical timeline record
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID REFERENCES candidates(id) ON DELETE SET NULL,
    patient_key TEXT NOT NULL,
    lab TEXT NOT NULL,
    report_id TEXT NOT NULL,
    test_name TEXT NOT NULL,
    report_date DATE NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT uq_reports_patient_report_id UNIQUE (patient_key, report_id),
    CONSTRAINT uq_reports_patient_sha256 UNIQUE (patient_key, sha256)
);

CREATE INDEX IF NOT EXISTS idx_reports_patient_key ON reports(patient_key);
CREATE INDEX IF NOT EXISTS idx_reports_report_date ON reports(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_reports_lab ON reports(lab);

-- 4. events table: Live log and audit trail
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'INFO', -- 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    message TEXT NOT NULL,
    data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_run_id_id ON events(run_id, id);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- 5. approvals table: Human-in-the-loop decisions and overrides
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    overrides JSONB, -- key: candidate_id, value: 'keep' | 'skip'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approvals_run_id ON approvals(run_id);
