CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS projet_prog;

CREATE TABLE IF NOT EXISTS documents (
    id bigserial PRIMARY KEY,
    content text,                    -- Le texte brut (pour le donner à l'IA)
    embedding public.vector(384)            -- Le vecteur mathématique
);

CREATE INDEX ON projet_prog.documents USING hnsw (embedding public.vector_cosine_ops); -- Indexation pour de meilleures performances