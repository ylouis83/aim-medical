CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE patient_profiles (
    patient_id TEXT PRIMARY KEY,
    name TEXT,
    date_of_birth DATE,
    sex TEXT,
    identifiers JSONB NOT NULL DEFAULT '{}'::jsonb,
    allergies JSONB NOT NULL DEFAULT '[]'::jsonb,
    conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_factors JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE encounters (
    encounter_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patient_profiles(patient_id),
    encounter_type TEXT NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    chief_complaint TEXT,
    assessment TEXT,
    plan TEXT,
    practitioner TEXT,
    facility TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE observations (
    observation_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patient_profiles(patient_id),
    encounter_id TEXT REFERENCES encounters(encounter_id),
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT,
    value_numeric DOUBLE PRECISION,
    unit TEXT,
    reference_range TEXT,
    observed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE medications (
    medication_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patient_profiles(patient_id),
    encounter_id TEXT REFERENCES encounters(encounter_id),
    name TEXT NOT NULL,
    indication TEXT,
    prescriber TEXT,
    dose TEXT,
    frequency TEXT,
    route TEXT,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    status TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patient_profiles(patient_id),
    encounter_id TEXT REFERENCES encounters(encounter_id),
    doc_type TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    source_uri TEXT,
    file_hash TEXT,
    extracted_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE memory_items (
    memory_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    kind TEXT NOT NULL,
    embedding vector(1536),
    user_id TEXT,
    patient_id TEXT,
    encounter_id TEXT,
    actor_role TEXT,
    confidence DOUBLE PRECISION,
    risk_level TEXT,
    tags TEXT[],
    extra JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INT NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE memory_item_sources (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL REFERENCES memory_items(memory_id),
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    page INT,
    span TEXT,
    version INT NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_encounters_patient_id ON encounters(patient_id);
CREATE INDEX idx_encounters_patient_time ON encounters(patient_id, start_time DESC);

CREATE INDEX idx_observations_patient_id ON observations(patient_id);
CREATE INDEX idx_observations_encounter_id ON observations(encounter_id);

CREATE INDEX idx_medications_patient_id ON medications(patient_id);

CREATE INDEX idx_documents_patient_id ON documents(patient_id);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);

CREATE INDEX idx_memory_items_patient_id ON memory_items(patient_id);
CREATE INDEX idx_memory_items_encounter_id ON memory_items(encounter_id);
CREATE INDEX idx_memory_items_patient_kind ON memory_items(patient_id, kind);

CREATE INDEX idx_memory_items_embedding ON memory_items
    USING hnsw (embedding vector_cosine_ops);
