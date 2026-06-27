-- ============================================================
-- ALDIMI Medical Document Management System — Database Schema
-- ============================================================

-- Custom ENUM types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('patient', 'doctor');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE document_type AS ENUM ('dni', 'medical_report');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_type AS ENUM ('critical_health', 'mental_health', 'medication_stock');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE message_role AS ENUM ('user', 'ai');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- 1. Users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dni             VARCHAR(8) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    firstname       VARCHAR(150) NOT NULL,
    lastname        VARCHAR(150) NOT NULL,
    birthdate       DATE NOT NULL,
    gender          VARCHAR(20) NOT NULL,
    address         TEXT NOT NULL,
    phone           VARCHAR(20),
    role            user_role NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================
-- 2. Documents (base table for both DNI and medical reports)
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            document_type NOT NULL,
    file_path       TEXT NOT NULL,
    ocr_text        TEXT,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type);

-- ============================================================
-- 3. DNI Documents (extension of documents table)
-- ============================================================
CREATE TABLE IF NOT EXISTS dni_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    names               VARCHAR(255) NOT NULL,
    paternal_lastname   VARCHAR(150) NOT NULL,
    maternal_lastname   VARCHAR(150) NOT NULL,
    date_of_birth       DATE NOT NULL,
    gender              VARCHAR(20) NOT NULL
);

-- ============================================================
-- 4. Medical Reports (extension of documents table)
-- ============================================================
CREATE TABLE IF NOT EXISTS medical_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    report_date     DATE NOT NULL,
    condition       TEXT NOT NULL,
    results         TEXT,
    medications     JSONB DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_medical_reports_condition ON medical_reports USING gin(to_tsvector('spanish', condition));

-- ============================================================
-- 5. Doctor — Patient relationship (many-to-many)
-- ============================================================
CREATE TABLE IF NOT EXISTS doctor_patient (
    doctor_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (doctor_id, patient_id),
    CHECK (doctor_id <> patient_id)
);

CREATE INDEX IF NOT EXISTS idx_doctor_patient_patient ON doctor_patient(patient_id);

-- ============================================================
-- 6. Chat Sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);

-- ============================================================
-- 7. Chat Messages
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role        message_role NOT NULL,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

-- ============================================================
-- 8. Alerts
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_type  alert_type NOT NULL,
    patient_id  UUID REFERENCES users(id) ON DELETE SET NULL,
    alert_text  TEXT NOT NULL,
    score_risk  DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (score_risk >= 0 AND score_risk <= 1),
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read ON alerts(is_read) WHERE is_read = FALSE;
CREATE INDEX IF NOT EXISTS idx_alerts_alert_type ON alerts(alert_type);

-- ============================================================
-- 9. Medication Inventory (company / clinic stock)
-- ============================================================
CREATE TABLE IF NOT EXISTS medication_inventory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL UNIQUE,
    quantity    INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    threshold   INTEGER NOT NULL DEFAULT 10 CHECK (threshold >= 0),
    unit        VARCHAR(50) NOT NULL DEFAULT 'units',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_medication_inventory_low_stock ON medication_inventory(quantity) WHERE quantity <= threshold;

-- ============================================================
-- 10. pgvector extension + Document Chunks (for RAG)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT NOT NULL,
    embedding       vector(384),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
