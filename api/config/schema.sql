-- =============================================================
-- HeLMO Oracle — Schéma PostgreSQL (Docker / hors Supabase)
-- Compatible pgvector/pgvector:pg17
-- =============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -------------------------------------------------------------
-- Documents (base de connaissances RAG)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
  id          SERIAL PRIMARY KEY,
  content     TEXT,
  vecteur     VECTOR(768),
  metadata    JSONB,
  chunk_hash  VARCHAR(64),
  ingested_at TIMESTAMPTZ DEFAULT now(),
  fts_vector  TSVECTOR
);

CREATE UNIQUE INDEX IF NOT EXISTS documents_chunk_hash_key
  ON documents (chunk_hash) WHERE chunk_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_cosine
  ON documents USING ivfflat (vecteur vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_documents_fts
  ON documents USING gin(fts_vector);

CREATE OR REPLACE FUNCTION update_fts_vector() RETURNS TRIGGER AS $$
BEGIN
  new.fts_vector := to_tsvector('french', new.content);
  RETURN new;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trig_update_fts
  BEFORE INSERT OR UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_fts_vector();

-- -------------------------------------------------------------
-- Sessions de conversation
-- (sans FK auth.users — sessions anonymes en mode Docker)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_sessions (
  session_id  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id     UUID,
  title       TEXT,
  provider    TEXT,
  model       TEXT,
  messages    JSONB DEFAULT '[]',
  summary     TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions (user_id);

-- -------------------------------------------------------------
-- Logs système
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS logs (
  id         UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  level      TEXT NOT NULL,
  source     TEXT NOT NULL,
  message    TEXT,
  metadata   JSONB,
  user_id    UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_logs_level  ON logs (level);
CREATE INDEX IF NOT EXISTS idx_logs_source ON logs (source);
CREATE INDEX IF NOT EXISTS idx_logs_date   ON logs (created_at DESC);

-- -------------------------------------------------------------
-- Feedbacks utilisateurs
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS feedback (
  id         UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  session_id TEXT,
  user_id    UUID,
  rating     SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment    TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback (session_id);

-- -------------------------------------------------------------
-- Profils utilisateurs
-- (table vide en mode Docker — pas d'auth Supabase)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  first_name TEXT,
  last_name  TEXT
);