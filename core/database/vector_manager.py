"""
Manages vector operations and hybrid search against the PostgreSQL/Supabase database.

Search strategy:
  - Semantic search  : cosine distance (<=>)  — finds conceptually similar content
  - BM25 / FTS       : PostgreSQL tsvector     — finds exact keyword matches
  - Hybrid fusion    : Reciprocal Rank Fusion  — merges both result lists optimally

Why cosine over euclidean (L2)?
  Cosine measures the angle between vectors, ignoring magnitude.
  For text embeddings, two semantically similar sentences may have different
  vector norms — cosine handles this correctly, L2 does not.

Why RRF over ColBERT re-ranking?
  RRF (Reciprocal Rank Fusion) is a proven, zero-dependency algorithm that
  consistently outperforms individual rankings. ColBERT adds ~300-500ms latency
  and an extra model dependency for marginal gains at this data scale.

  RRF formula: score(d) = Σ 1 / (k + rank(d))
  where k=60 is the standard constant that dampens the influence of high ranks.
"""

import json
from datetime import datetime, timezone
from typing import List, Tuple, Dict

import psycopg
import streamlit as st
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pgvector.psycopg import register_vector

from core.utils.utils import _load_config

config = _load_config()

_SEARCH_CFG = config.get("search", {})
_K_SEMANTIC = _SEARCH_CFG.get("k_semantic", 10)
_K_BM25 = _SEARCH_CFG.get("k_bm25", 10)
_K_FINAL = _SEARCH_CFG.get("k_final", 5)
_RRF_K = _SEARCH_CFG.get("rrf_k", 60)
_FTS_LANG = _SEARCH_CFG.get("fts_language", "french")


class VectorManager:
    """
    Handles connections to PostgreSQL/Supabase and manages hybrid search.

    ── Required SQL (run once in Supabase SQL editor) ──────────────

    -- 1. Add ingested_at column (if not already done)
    ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ DEFAULT now();

    -- 2. Add tsvector column for BM25/FTS
    ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS fts_vector TSVECTOR;

    -- 3. Populate fts_vector for existing rows
    UPDATE documents
        SET fts_vector = to_tsvector('french', content);

    -- 4. Create GIN index for fast full-text search
    CREATE INDEX IF NOT EXISTS idx_documents_fts
        ON documents USING GIN(fts_vector);

    -- 5. Create cosine distance index
    CREATE INDEX IF NOT EXISTS idx_documents_cosine
        ON documents USING ivfflat (vecteur vector_cosine_ops)
        WITH (lists = 100);

    -- 6. Trigger to auto-update fts_vector on insert/update
    CREATE OR REPLACE FUNCTION update_fts_vector()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.fts_vector := to_tsvector('french', NEW.content);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE OR REPLACE TRIGGER trig_update_fts
        BEFORE INSERT OR UPDATE ON documents
        FOR EACH ROW EXECUTE FUNCTION update_fts_vector();
    ────────────────────────────────────────────────────────────────
    """

    def __init__(self, embeddings_model=None):
        if "connection_string" in config["database"]:
            self.conn = psycopg.connect(
                config["database"]["connection_string"],
                autocommit=True,
            )
        else:
            self.conn = psycopg.connect(
                host=config["database"]["host"],
                dbname=config["database"]["dbname"],
                user=config["database"]["user"],
                password=config["database"]["password"],
                port=int(config["database"]["port"]),
                sslmode="require",
            )

        register_vector(self.conn)

        # Accept an externally shared embedding model to avoid duplicate PyTorch
        # instantiation. Always pass the singleton from app.py via get_vector_manager().
        # If None (e.g. called from ingestion.py), creates its own instance.
        if embeddings_model is not None:
            self.embeddings_model = embeddings_model
        else:
            # Modèle performant du MTEB (768 dimensions)
            self.embeddings_model = HuggingFaceEmbedding(
                model_name="intfloat/multilingual-e5-base"
            )

    # ─────────────────────────────────────────────────────────────
    # INSERT
    # ─────────────────────────────────────────────────────────────

    def add_document(self, text: str, metadata: dict = None) -> None:
        """
        Generates an embedding and saves the text with metadata and ingestion timestamp.
        The fts_vector column is populated automatically by the database trigger.
        """
        if metadata is None:
            metadata = {}

        text_to_embed = text

        if "global_context" in metadata:
            text_to_embed = f"Global Context: {metadata['global_context']}\n\nContent: {text}"
        elif "Header 1" in metadata:
            text_to_embed = f"Chapter: {metadata['Header 1']}\n\nContent: {text}"
        elif "category" in metadata and "item_name" in metadata:
            text_to_embed = f"Category: {metadata['category']} | Item: {metadata['item_name']}\n\nContent: {text}"

        vector = self.embeddings_model.get_text_embedding(text_to_embed)
        ingested_at = datetime.now(timezone.utc)

        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (content, vecteur, metadata, ingested_at) VALUES (%s, %s, %s, %s)",
                (text, vector, json.dumps(metadata), ingested_at),
            )
        self.conn.commit()

    # ─────────────────────────────────────────────────────────────
    # SEARCH — Semantic cosine
    # ─────────────────────────────────────────────────────────────

    def search_semantic(
            self, query_vector: List[float], k: int = _K_SEMANTIC
    ) -> List[Tuple[str, float, dict]]:
        """
        Cosine similarity search (<=>) — finds semantically related content.
        Lower score = more similar (cosine distance, not similarity).
        Returns list of (content, distance, metadata).
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, vecteur <=> %s::vector AS distance, metadata
                FROM documents
                ORDER BY distance
                    LIMIT %s
                """,
                (query_vector, k),
            )
            return cur.fetchall()

    # ─────────────────────────────────────────────────────────────
    # SEARCH — BM25 / Full-Text Search
    # ─────────────────────────────────────────────────────────────

    def search_bm25(
            self, query: str, k: int = _K_BM25
    ) -> List[Tuple[str, float, dict]]:
        """
        PostgreSQL Full-Text Search — finds exact keyword and term matches.
        Uses ts_rank for scoring (approximates BM25 behaviour natively).
        Falls back gracefully if fts_vector column doesn't exist yet.
        Returns list of (content, rank_score, metadata).
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT content,
                           ts_rank(fts_vector, plainto_tsquery('{_FTS_LANG}', %s)) AS rank,
                           metadata
                    FROM documents
                    WHERE fts_vector @@ plainto_tsquery('{_FTS_LANG}', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                    """,
                    (query, query, k),
                )
                return cur.fetchall()
        except Exception as e:
            print(f"  ⚠️  BM25 unavailable ({e}) — semantic-only fallback active")
            return []

    # ─────────────────────────────────────────────────────────────
    # SEARCH — Hybrid RRF fusion
    # ─────────────────────────────────────────────────────────────

    def search_hybrid(
            self,
            query: str,
            query_vector: List[float],
            k_final: int = _K_FINAL,
    ) -> List[Tuple[str, float, dict]]:
        """
        Hybrid search: semantic cosine + BM25, fused with Reciprocal Rank Fusion.

        RRF score = Σ  1 / (rrf_k + rank_position)

        Documents appearing in BOTH result lists get a cumulative RRF boost,
        making them rank higher — exactly what you want for high-confidence results.
        Documents found only by BM25 (exact name match) are still surfaced even
        if semantically distant.

        Returns list of (content, rrf_score, metadata), best first.
        """
        semantic_results = self.search_semantic(query_vector, k=_K_SEMANTIC)
        bm25_results = self.search_bm25(query, k=_K_BM25)

        rrf_scores: Dict[str, float] = {}
        doc_store: Dict[str, Tuple] = {}

        for rank, (content, score, metadata) in enumerate(semantic_results):
            rrf_scores[content] = rrf_scores.get(content, 0.0) + 1.0 / (_RRF_K + rank + 1)
            doc_store[content] = (content, score, metadata)

        for rank, (content, score, metadata) in enumerate(bm25_results):
            rrf_scores[content] = rrf_scores.get(content, 0.0) + 1.0 / (_RRF_K + rank + 1)
            doc_store[content] = (content, score, metadata)

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return [
            (doc_store[content][0], rrf_score, doc_store[content][2])
            for content, rrf_score in sorted_docs[:k_final]
        ]

    # ─────────────────────────────────────────────────────────────
    # DATABASE EXPLORER
    # ─────────────────────────────────────────────────────────────

    def list_sources(self) -> list[dict]:
        """
        Returns one entry per unique source file in the database.
        Each entry: { source, chunk_count, global_context, ingested_at }
        Groups by source filename — not by individual chunk.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                            SELECT metadata ->>'source' AS source, COUNT (*) AS chunk_count, MAX (metadata->>'global_context') AS global_context, MAX (ingested_at) AS ingested_at
                            FROM documents
                            WHERE metadata->>'source' IS NOT NULL
                            GROUP BY metadata->>'source'
                            ORDER BY MAX (ingested_at) DESC NULLS LAST
                            """)
                rows = cur.fetchall()
                return [
                    {
                        "source": r[0],
                        "chunk_count": r[1],
                        "global_context": r[2] or "Aucun contexte global disponible.",
                        "ingested_at": r[3].strftime("%Y-%m-%d %H:%M UTC") if r[3] else "—",
                    }
                    for r in rows
                ]
        except Exception as e:
            print(f"⚠️  list_sources failed: {e}")
            return []

    # ─────────────────────────────────────────────────────────────
    # LEGACY
    # ─────────────────────────────────────────────────────────────

    def search_similar(
            self, query_vector: List[float], k: int = _K_FINAL
    ) -> List[Tuple[str, float, dict]]:
        """Alias for search_semantic() — kept for backward compatibility."""
        return self.search_semantic(query_vector, k)
