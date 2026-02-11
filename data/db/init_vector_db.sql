CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS projet_prog;

CREATE TABLE documents (
    id bigserial PRIMARY KEY,
    content text,                    -- Le texte brut (pour le donner à l'IA)
    embedding vector(384)            -- Le vecteur mathématique
);

CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops); -- Indexation pour de meilleures performances

