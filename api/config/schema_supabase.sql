-- =============================================================
-- HELMo Oracle — Schéma Supabase
--
-- Différences vs schema_docker.sql (Docker) :
--   • gen_random_uuid() remplace uuid_generate_v4() (pas besoin de uuid-ossp)
--   • profiles.id référence auth.users(id) (intégration Supabase Auth)
--   • chat_sessions.user_id référence auth.users(id)
--   • RLS activé sur tous les tableaux + politiques corrigées
--   • ALTER POLICY supprimés (remplacés par CREATE POLICY complets)
--
-- Prérequis : activer l'extension "vector" via le dashboard Supabase
--   Settings > Database > Extensions > vector
-- =============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- -------------------------------------------------------------
-- Documents (base de connaissances RAG)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.documents (
  id          BIGSERIAL PRIMARY KEY,
  content     TEXT,
  vecteur     VECTOR(768),
  metadata    JSONB,
  chunk_hash  VARCHAR(64),
  ingested_at TIMESTAMPTZ DEFAULT now(),
  fts_vector  TSVECTOR
);

CREATE UNIQUE INDEX IF NOT EXISTS documents_chunk_hash_key
  ON public.documents (chunk_hash) WHERE chunk_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_cosine
  ON public.documents USING ivfflat (vecteur vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_documents_fts
  ON public.documents USING gin(fts_vector);

CREATE OR REPLACE FUNCTION update_fts_vector() RETURNS TRIGGER AS $$
BEGIN
  new.fts_vector := to_tsvector('french', coalesce(new.content, ''));
  RETURN new;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trig_update_fts ON public.documents;
CREATE TRIGGER trig_update_fts
  BEFORE INSERT OR UPDATE ON public.documents
  FOR EACH ROW EXECUTE FUNCTION update_fts_vector();

-- -------------------------------------------------------------
-- Sessions de conversation
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.chat_sessions (
  session_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title       TEXT,
  provider    TEXT,
  model       TEXT,
  messages    JSONB DEFAULT '[]',
  summary     TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON public.chat_sessions (user_id);

-- -------------------------------------------------------------
-- Logs système
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.logs (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  level      TEXT NOT NULL,
  source     TEXT NOT NULL,
  message    TEXT,
  metadata   JSONB,
  user_id    UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_logs_level  ON public.logs (level);
CREATE INDEX IF NOT EXISTS idx_logs_source ON public.logs (source);
CREATE INDEX IF NOT EXISTS idx_logs_date   ON public.logs (created_at DESC);

-- -------------------------------------------------------------
-- Feedbacks utilisateurs
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.feedback (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  session_id TEXT,
  user_id    UUID,
  rating     SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment    TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_session ON public.feedback (session_id);

-- -------------------------------------------------------------
-- Profils utilisateurs (liés à Supabase Auth)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
  id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  first_name TEXT,
  last_name  TEXT
);

-- =============================================================
-- Row Level Security
-- =============================================================
ALTER TABLE public.documents     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.logs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles      ENABLE ROW LEVEL SECURITY;

-- documents : le back-end utilise service_role (bypass RLS automatique).
-- On autorise la lecture en SELECT pour les clients authentifiés.
CREATE POLICY "Lecture documents"
  ON public.documents FOR SELECT
  TO authenticated
  USING (true);

-- chat_sessions : isolement strict par utilisateur
CREATE POLICY "Gestion propres sessions"
  ON public.chat_sessions FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- feedback : insertion uniquement (pas de lecture côté front)
CREATE POLICY "Insertion feedback"
  ON public.feedback FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- logs : le back-end écrit via service_role ; le front peut insérer
CREATE POLICY "Insertion logs"
  ON public.logs FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- profiles : lecture publique pour les utilisateurs connectés
CREATE POLICY "Lecture publique profils"
  ON public.profiles FOR SELECT
  TO authenticated
  USING (true);

-- profiles : mise à jour uniquement de son propre profil
CREATE POLICY "Mise à jour propre profil"
  ON public.profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);
