-- =============================================================
-- HELMo Oracle — Schéma PostgreSQL Serveur (Production)
-- Compatible pgvector/pgvector:pg17
--
-- Usage : base vectorielle locale sur le serveur (Digital Ocean).
-- Contient UNIQUEMENT la table documents (base de connaissances RAG).
-- Sessions, logs, feedback, profiles → Supabase (avec RLS).
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
