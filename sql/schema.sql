-- Personal Health Record Organizer Database Schema
-- Compatible with Neon Postgres / PostgreSQL 14+
-- All tables are completely isolated inside the 'phr' schema

-- 0. Schema Creation and Path Setup
CREATE SCHEMA IF NOT EXISTS phr;
SET search_path TO phr, public;

-- Enable uuid generation if available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. users table: User accounts and authentication (isolated in phr)
CREATE TABLE IF NOT EXISTS phr.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phr_users_email ON phr.users(email);

-- 2. auth_sessions table: User session tokens (isolated in phr)
CREATE TABLE IF NOT EXISTS phr.auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES phr.users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phr_auth_sessions_user_id ON phr.auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_phr_auth_sessions_expires_at ON phr.auth_sessions(expires_at);

-- 3. user_labs table: Custom lab portals configured by users (isolated in phr)
CREATE TABLE IF NOT EXISTS phr.user_labs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES phr.users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    username TEXT DEFAULT '',
    password TEXT DEFAULT '',
    layout TEXT NOT NULL DEFAULT 'table',
    has_captcha BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_phr_user_lab_key UNIQUE (user_id, key)
);

CREATE INDEX IF NOT EXISTS idx_phr_user_labs_user_id ON phr.user_labs(user_id);

-- 4. runs table: Orchestration and patient run metadata (isolated in phr)
CREATE TABLE IF NOT EXISTS phr.runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES phr.users(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_phr_runs_user_id ON phr.runs(user_id);
CREATE INDEX IF NOT EXISTS idx_phr_runs_patient_key ON phr.runs(patient_key);
CREATE INDEX IF NOT EXISTS idx_phr_runs_status ON phr.runs(status);
CREATE INDEX IF NOT EXISTS idx_phr_runs_created_at ON phr.runs(created_at DESC);

-- 5. candidates table: Downloaded files and staging area (isolated in phr)
CREATE TABLE IF NOT EXISTS phr.candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES phr.runs(id) ON DELETE CASCADE,
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
    
    CONSTRAINT uq_phr_run_lab_filename UNIQUE (run_id, lab, filename)
);

CREATE INDEX IF NOT EXISTS idx_phr_candidates_run_id ON phr.candidates(run_id);
CREATE INDEX IF NOT EXISTS idx_phr_candidates_decision ON phr.candidates(decision);
CREATE INDEX IF NOT EXISTS idx_phr_candidates_status ON phr.candidates(status);
CREATE INDEX IF NOT EXISTS idx_phr_candidates_sha256 ON phr.candidates(sha256);

-- 6. reports table: The permanent medical timeline record (isolated in phr)
CREATE TABLE IF NOT EXISTS phr.reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES phr.users(id) ON DELETE CASCADE,
    candidate_id UUID REFERENCES phr.candidates(id) ON DELETE SET NULL,
    patient_key TEXT NOT NULL,
    lab TEXT NOT NULL,
    report_id TEXT NOT NULL,
    test_name TEXT NOT NULL,
    report_date DATE NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phr_reports_user_id ON phr.reports(user_id);
CREATE INDEX IF NOT EXISTS idx_phr_reports_patient_key ON phr.reports(patient_key);
CREATE INDEX IF NOT EXISTS idx_phr_reports_report_date ON phr.reports(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_phr_reports_lab ON phr.reports(lab);
CREATE UNIQUE INDEX IF NOT EXISTS uq_phr_reports_user_sha256 ON phr.reports (COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid), sha256);
CREATE UNIQUE INDEX IF NOT EXISTS uq_phr_reports_user_lab_report ON phr.reports (COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid), lab, report_id);

-- 7. events table: Live log and audit trail (isolated in phr)
CREATE TABLE IF NOT EXISTS phr.events (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES phr.runs(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'INFO', -- 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    message TEXT NOT NULL,
    data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phr_events_run_id_id ON phr.events(run_id, id);
CREATE INDEX IF NOT EXISTS idx_phr_events_created_at ON phr.events(created_at);

-- 8. approvals table: Human-in-the-loop decisions and overrides (isolated in phr)
CREATE TABLE IF NOT EXISTS phr.approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES phr.runs(id) ON DELETE CASCADE,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    overrides JSONB, -- key: candidate_id, value: 'keep' | 'skip'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phr_approvals_run_id ON phr.approvals(run_id);
