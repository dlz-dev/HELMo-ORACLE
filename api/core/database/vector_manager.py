"""
Manages vector operations and hybrid search against the PostgreSQL/Supabase database.

Search strategy:
  - Semantic search (cosine distance): finds conceptually similar content.
  - BM25 / FTS (tsvector): finds exact keyword matches.
  - Hybrid fusion (RRF): merges both result lists optimally.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from psycopg import sql
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pgvector.psycopg import register_vector

from core.utils.utils import FTS_LANG, K_BM25, K_FINAL, K_SEMANTIC, RRF_K, load_config



class VectorManager:
    """Handles connections to PostgreSQL/Supabase and manages hybrid search execution."""

    def __init__(self, embeddings_model: Any = None) -> None:
        """Initializes database connection and embedding model."""
        config = load_config()
        db_config = config.get("database", {})

        if "connection_string" in db_config:
            self.conn = psycopg.connect(db_config["connection_string"], autocommit=True)
        else:
            self.conn = psycopg.connect(
                host=db_config.get("host"),
                dbname=db_config.get("dbname"),
                user=db_config.get("user"),
                password=db_config.get("password"),
                port=int(db_config.get("port", 5432)),
                sslmode="require",
                autocommit=True,
            )

        register_vector(self.conn)

        self.embeddings_model = embeddings_model or HuggingFaceEmbedding(
            model_name="intfloat/multilingual-e5-base"
        )

    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Generates an embedding and saves the text with metadata and ingestion timestamp.
        The fts_vector column is populated automatically by the database trigger.
        """
        metadata = metadata or {}
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

    def search_semantic(
        self, query_vector: List[float], k: int = K_SEMANTIC
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Executes cosine similarity search (<=>).
        
        Args:
            query_vector: The vectorized user query.
            k: Number of semantic results to retrieve.
            
        Returns:
            List of tuples containing (content, distance, metadata).
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

    def search_bm25(self, query: str, k: int = K_BM25) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Executes PostgreSQL Full-Text Search for exact keyword matches.
        
        Args:
            query: The raw string user query.
            k: Number of exact match results to retrieve.
            
        Returns:
            List of tuples containing (content, rank_score, metadata).
        """
        try:
            with self.conn.cursor() as cur:
                query_sql = sql.SQL(
                    """
                    SELECT content,
                           ts_rank(fts_vector, plainto_tsquery({lang}, %s)) AS rank,
                           metadata
                    FROM documents
                    WHERE fts_vector @@ plainto_tsquery({lang}, %s)
                    ORDER BY rank DESC
                    LIMIT %s
                    """
                ).format(lang=sql.Literal(FTS_LANG))
                
                cur.execute(query_sql, (query, query, k))
                return cur.fetchall()
        except Exception as e:
            print(f"⚠️ BM25 unavailable ({e}) — semantic-only fallback active")
            return []

    def search_hybrid(
        self, query: str, query_vector: List[float], k_final: int = K_FINAL
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Combines semantic cosine and BM25 searches using Reciprocal Rank Fusion.
        
        Args:
            query: Raw string query for exact matching.
            query_vector: Vectorized query for semantic matching.
            k_final: Total number of fused results to return.
            
        Returns:
            List of tuples containing (content, rrf_score, metadata) ordered by best score.
        """
        semantic_results = self.search_semantic(query_vector, k=K_SEMANTIC)
        bm25_results = self.search_bm25(query, k=K_BM25)

        rrf_scores: Dict[str, float] = {}
        doc_store: Dict[str, Tuple[str, float, Dict[str, Any]]] = {}

        for rank, (content, score, metadata) in enumerate(semantic_results):
            rrf_scores[content] = rrf_scores.get(content, 0.0) + 1.0 / (RRF_K + rank + 1)
            doc_store[content] = (content, score, metadata)

        for rank, (content, score, metadata) in enumerate(bm25_results):
            rrf_scores[content] = rrf_scores.get(content, 0.0) + 1.0 / (RRF_K + rank + 1)
            doc_store[content] = (content, score, metadata)

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return [
            (doc_store[content][0], rrf_score, doc_store[content][2])
            for content, rrf_score in sorted_docs[:k_final]
        ]

    def list_sources(self) -> List[Dict[str, Any]]:
        """
        Aggregates database entries to return unique source files.
        
        Returns:
            List of dictionaries containing source metrics and metadata.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        metadata ->>'source' AS source, 
                        COUNT (*) AS chunk_count, 
                        MAX (metadata->>'global_context') AS global_context, 
                        MAX (ingested_at) AS ingested_at
                    FROM documents
                    WHERE metadata->>'source' IS NOT NULL
                    GROUP BY metadata->>'source'
                    ORDER BY MAX (ingested_at) DESC NULLS LAST
                    """
                )
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
            print(f"⚠️ list_sources failed: {e}")
            return []

    def search_similar(
        self, query_vector: List[float], k: int = K_FINAL
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Alias for search_semantic() — kept for backward compatibility."""
        return self.search_semantic(query_vector, k)